import os
import re
import psycopg2
import pandas as pd
import chromadb
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from ollama import Client
from flashrank import Ranker, RerankRequest
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import torch
import json
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Initialize Firebase Admin SDK
current_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(current_dir, "firebase-key.json")

cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

print("[INITIALIZATION] Loading BGE Multilingual Reranker (BAAI/bge-reranker-v2-m3)")
try:
    # We load BGE v2 M3 as a Sequence Classification model for blazing-fast local cross-encoding
    bge_model_name = "BAAI/bge-reranker-v2-m3"
    bge_tokenizer = AutoTokenizer.from_pretrained(bge_model_name)
    bge_model = AutoModelForSequenceClassification.from_pretrained(bge_model_name)
    bge_model.eval() # Set to evaluation mode to save memory
    print("[INITIALIZATION] BGE Multilingual Reranker loaded successfully!")
except Exception as model_err:
    print(f"🚨 [CRITICAL ERROR] Failed to load BGE Reranker: {model_err}")
    bge_model = None

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- 1. CORE OFFLINE VANNA PIPELINE CLASS ---
class MyPrivateVanna:
    def __init__(self, model_name="qwen3.5:9b"):
        self.model_name = model_name
        self.chroma_client = chromadb.PersistentClient(path="./vanna_knowledge_base")
        self.collection = self.chroma_client.get_or_create_collection("vanna_collection")
        self.conn = None

    def connect_to_postgres(self, host, dbname, user, password="", port=5432):
        self.conn = psycopg2.connect(host=host, database=dbname, user=user, password=password, port=port)
        print(f"Connected successfully to database: {dbname}")

    def generate_sql(self, question):
        start_time=datetime.now(timezone.utc)
        print(start_time)
        # 1. Instruct Ollama to translate the entire sentence to Indonesian
        translation_prompt = (
            f"You are a bilingual database administrator translation assistant.\n"
            f"Context: The user is querying the database of ITS university (Institut Teknologi Sepuluh Nopember)"
            f"Task: Convert the user's data request into a concise, natural Indonesian sentence"
            f"using formal database schema and academic data warehouse terminology.\n\n"
            f"User Request: {question}\n"
            f"CRITICAL: Output ONLY the translated Indonesian sentence. Do not include introductory text, explanations, or quotes."
        )
        
        indonesian_sentence = ""
        try:
            res = ollama_client.chat(model=self.model_name, messages=[{"role": "user", "content": translation_prompt}])
            indonesian_sentence = res["message"]["content"].strip().strip('"').strip("'")
            print(f"🌐 [TRANSLATION LAYER] Input: '{question}' ──> Chroma Query: '{indonesian_sentence}'")
        except Exception as e:
            print(f"⚠️ Translation layer failed, using original query. Error: {e}")
            indonesian_sentence = question

        #Querying Chromadb to fetch candidates
        chroma_results = self.collection.query(query_texts=[indonesian_sentence], n_results=15)
        
        if not chroma_results["documents"] or not chroma_results["documents"][0]:
            schema_context = "No relevant tables found in the database knowledge base."
        else:
            raw_docs = chroma_results["documents"][0]
            raw_ids = chroma_results["ids"][0]
            
            if bge_model is not None:
                # Build cross-encoding evaluation pairs matching the original English question to the Indonesian DDL text blocks
                # BGE M3 handles this cross-lingual mapping natively!
                eval_pairs = [[question, doc_text] for doc_text in raw_docs]
                
                with torch.no_grad():
                    inputs = bge_tokenizer(eval_pairs, padding=True, truncation=True, return_tensors='pt', max_length=512)
                    logits = bge_model(**inputs, return_dict=True).logits.view(-1,).float()
                    scores = logits.tolist()
                
                # Pair original schemas with their multilingual BGE confidence scores
                scored_schemas = []
                for idx, (doc_id, doc_text) in enumerate(zip(raw_ids, raw_docs)):
                    scored_schemas.append({
                        "id": doc_id,
                        "text": doc_text,
                        "score": scores[idx]
                    })
                
                # Sort descending to pull the highest confidence matches to the top
                scored_schemas.sort(key=lambda x: x["score"], reverse=True)
                
                # Select the top 3 absolute best matches
                top_schemas = scored_schemas[:3]
                schema_context = "\n\n".join([p["text"] for p in top_schemas])
                
                print("\n" + "═"*60)
                print("schema_context: ",schema_context) #debug
                print(" 🎯 [BGE MULTILINGUAL ACTIVE] TABLE SCHEMA RE-RANKING MATCHES:")
                for idx, p in enumerate(top_schemas):
                    print(f"   {idx+1}. ID: {p['id']} (BGE Logit Score: {p['score']:.4f})")
                print("═"*60)
            else:
                # Fallback directly to Chroma ranking if the BGE model was not initialized
                schema_context = "\n\n".join(raw_docs[:3])
                print("\n⚠️ [BGE FALLBACK] Running direct Chroma vector matches...")

        # 2. Force-inject additional schema context based on keyword detection
        q_lower = indonesian_sentence.lower() + " " + question.lower()

        schema_dim_mahasiswa = """Database Table Definition Asset:
    Table: akademik.dim_mahasiswa
    Description: Comprehensive master registry containing demographic profiles, family, and high school metadata for all registered students.
    Columns:
    - id_mahasiswa (character varying) -- Primary database key representing a student
    - nama (character varying) -- Student's full name
    - nim (character varying) -- National student registration number / NRP (Nomor Registrasi Pokok)
    - tanggal_lahir (timestamp without time zone) -- Student's birth date
    - id_jenis_kelamin (character varying) -- 'L' for Laki-laki (Male), 'P' for Perempuan (Female)
    - nama_jenis_kelamin (character varying) -- Sex details: 'Laki-laki' or 'Perempuan'
    - id_kota_lahir (character varying) -- Birth city identifier
    - nama_kota_lahir (character varying) -- Birth city name
    - id_kewarganegaraan (character varying) -- Citizenship code
    - nama_kewarganegaraan (character varying) -- Country of citizenship
    - periode_masuk (character varying) -- First semester period code of student entry (e.g., '20241')
    - periode_keluar (character varying) -- Exit/Graduation semester period code (if graduated)
    - id_slta (character varying) -- High school identifier
    - nama_slta (character varying) -- High school name (SLTA / SMA / SMK / MA)
    - id_kota_slta (character varying) -- High school city identifier
    - nama_kota_slta (character varying) -- High school city location
    - id_provinsi_slta (character varying) -- High school province identifier
    - nama_provinisi_slta (character varying) -- High school province location (e.g., 'Jawa Timur', 'DKI Jakarta')
    - tahun_ijazah_slta (smallint) -- High school graduation year
    - nisn (character varying) -- National student index number (NISN)
    - jumlah_saudara (smallint) -- Total number of siblings
    - jumlah_kakak (integer) -- Number of older siblings
    - jumlah_adik (integer) -- Number of younger siblings
    - nama_ayah (character varying) -- Father's full name
    - nik_ayah (character varying) -- Father's citizen ID
    - id_pekerjaan_ayah (character varying) -- Father's occupation ID
    - nama_pekerjaan_ayah (character varying) -- Father's job (e.g., 'PNS', 'Karyawan Swasta', 'Wiraswasta')
    - pendidikan_ayah (character varying) -- Father's highest education degree
    - gaji_ayah (integer) -- Father's monthly income value (use for filtering high salary parents)
    - is_ayah_berpenghasilan (integer) -- 1 if father is earning, 0 otherwise
    - status_hidup_ayah (character varying) -- Father's life status (e.g., 'Hidup', 'Wafat')
    - nama_ibu (character varying) -- Mother's full name
    - nik_ibu (character varying) -- Mother's citizen ID
    - id_pekerjaan_ibu (character varying) -- Mother's occupation ID
    - nama_pekerjaan_ibu (character varying) -- Mother's job (e.g., 'Ibu Rumah Tangga', 'Guru', 'PNS')
    - gaji_ibu (integer) -- Mother's monthly income value
    - is_ibu_berpenghasilan (integer) -- 1 if mother is earning, 0 otherwise
    - status_hidup_ibu (character varying) -- Mother's life status (e.g., 'Hidup', 'Wafat')
    - nama_wali (character varying) -- Legal guardian's full name
    - nik_wali (character varying) -- Guardian's citizen ID
    - id_pekerjaan_wali (character varying) -- Guardian's occupation ID
    - nama_pekerjaan_wali (character varying) -- Guardian's job
    - pendidikan_wali (character varying) -- Guardian's education degree
    - hubungan_wali (character varying) -- Relationship to guardian
    - id_bidang_studi (integer) -- Major field of study index key : FK linking to dim_bidang_studi.id
    - nama_bidang_studi (character varying) -- Official major field of study name
    - id_status_aktif_terakhir (character varying) -- Status 'L' for Lulus
    - nama_status_aktif_terakhir (character varying) -- Textual status description (e.g., 'Aktif', 'Lulus', 'Cuti', 'Keluar', 'DO')
    - nomor_pendaftaran (character varying) -- Enrollment/Admission registration index
    - id_mahasiswa_itsdw (bigint) -- Data Warehouse legacy mapping key
    - nrp_lama_siakad (character varying) -- Old student register format
    - tahun_masuk (integer) -- Student's enrollment year (e.g., 2024. Use this to filter by student cohort or batch/angkatan)
    - tahun_keluar (integer) -- Year student completed studies or graduated
    - id (bigint) -- Sequence ID
    - version (integer) -- Version tracking index
    - id_prodi (integer) -- Study program key
    - nama_prodi (character varying) -- Official Department major program name (e.g., 'Teknik Informatika', 'Sistem Informasi')
    - id_departemen (integer) -- Department parent key
    - nama_departemen (character varying) -- Parent department name
    - id_fakultas (integer) -- Faculty parent key
    - nama_fakultas (character varying) -- Faculty name (e.g., 'Fakultas Teknologi Informasi dan Komunikasi', 'ELECTICS')
    - nama_pendek_fakultas (character varying) -- Shortened code (e.g., 'FTIK', 'FTEIC')
    - jalur_studi_ditempuh (character varying) -- Study pathway type
    - jalur_lanjut_studi (character varying) -- Continued study details (if transfer)
    - nrp_lama_siakad_sebelum_lanjut_studi (character varying) -- Transfer history
    - nrp_lama_siakad_lanjut_studi (character varying) -- Transfer current mapping
    - id_jalur_diterima (character varying) -- Admission path ID
    - nama_jalur_diterima (character varying) -- Official entry selection path (e.g., 'SNBP', 'SNBT', 'Mandiri')
    - id_program (character varying) -- Program type ID
    - nama_program (character varying) -- Program class (e.g., 'Reguler', 'S1 Mandiri')
    - sso_id (character varying) -- Single Sign-On account ID
    - jenjang (character varying) -- Study level: 'S1' (Bachelor), 'S2' (Master), 'S3' (Doctoral), 'D3' (Diploma III), 'D4' (Diploma IV)
    - is_iup (integer) -- International program flag: 1 = IUP class student, 0 = Regular class student
    - tanggal_kelulusan (date) -- Formal date student was declared a graduate
    - tanggal_wisuda (date) -- Actual graduation ceremony date
    - judul_ta (character varying) -- Final thesis / Skripsi / Tugas Akhir project title string
    - wisuda_ke (integer) -- Graduation batch number sequence (e.g., 129, 130)
    - status_aktif_simple_terakhir (character varying) -- Simplified state: 'Aktif', 'Lulus', 'Cuti', 'Keluar', 'DO'
    - email (character varying) -- Student's email contact
    - telepon (character varying) -- Student's home phone number
    - jenis_asing (character varying) -- Foreign student nationality category
    - is_asing (integer) -- 1 if student is a foreign national, 0 for Indonesian citizens"""

        schema_dim_pegawai = """Database Table Definition Asset:
    Table: kepegawaian.dim_pegawai
    Description: Comprehensive master registry containing personal profile, demographic details, degrees, rank, and identifiers of all university staff (lecturers and administrative personnel).
    Columns:
    - id_pegawai (character varying) -- Unique employee identifier key
    - id_sdm_mihc (character varying) -- SDM system identity key
    - nip (character varying) -- Official national civil servant registration number (NIP / NIP Akademik)
    - id_simpeg_mihc (character varying) -- Simpeg application code
    - nip_akademik_simpeg (character varying) -- Academic NIP code
    - id_jenis_pegawai (integer) -- Employee type code: 1 = Dosen (Lecturer/Teacher/Academic staff), 2 = Tendik (Tenaga Kependidikan/Administrative/Support staff)
    - jenis_pegawai (character varying) -- Staff type description: 'Dosen' (Teachers/Faculty members/Lecturers/Civitas Akademika), 'Tendik' (Support staff/Administrators/Librarians/Operators)
    - nama (character varying) -- Employee's full name
    - nama_versi_akademik (character varying) -- Academic formatted name
    - nama_versi_kepegawaian (character varying) -- HR application name
    - status_pegawai (character varying) -- Employment status: 'PNS' (Civil Servant), 'Non-PNS' (Permanent Contract), 'Kontrak' (Temporary), 'Honorer' (Casual worker)
    - tanggal_masuk (timestamp without time zone) -- Date employee started working
    - tanggal_keluar (timestamp without time zone) -- Date employee left or retired
    - id_status_aktif (character varying) -- Status flag key
    - nama_status_aktif (character varying) -- Full active status description (e.g., 'Aktif', 'Cuti', 'Pensiun', 'Keluar')
    - status_aktif_simple (character varying) -- Simplified active state: 'IN' or 'OUT'
    - id_satker (character varying) -- Working unit ID code
    - unit (character varying) -- Operational working unit name
    - jurusan (character varying) -- Academic major department under which the lecturer resides
    - fakultas (character varying) -- Parent faculty name (e.g., 'FTEIC', 'FTIK')
    - nama_fungsional (character varying) -- Academic rank: 'Asisten Ahli', 'Lektor', 'Lektor Kepala', 'Guru Besar' (Professor)
    - level_jfungsional (smallint) -- Numeric rank level index
    - nilai_jfungsional (integer) -- Numeric rank score mapping
    - tmt_jfungsional (timestamp without time zone) -- TMT date for academic rank
    - nama_jabatan_umum (character varying) -- General general/non-academic staff rank description
    - level_jumum (smallint) -- General position level index
    - nilai_jumum (integer) -- General position score mapping
    - tmt_jabatan_umum (timestamp without time zone) -- General position TMT date
    - jenis_kelamin (character varying) -- Sex details: 'L' for Laki-laki or 'P' for Perempuan
    - tempat_lahir (character varying) -- Birth city location
    - tgl_lahir (timestamp without time zone) -- Date of birth
    - agama (character varying) -- Employee's declared religion
    - nik (character varying) -- National identity card number (NIK)
    - npwp (character varying) -- Tax registry number (NPWP)
    - no_rekening (character varying) -- Payroll bank account
    - alamat (character varying) -- Current residential address
    - alamat_ktp (character varying) -- Legal ID card address
    - telepon (character varying) -- Fixed telephone contact
    - no_hp (character varying) -- Mobile phone number
    - email (character varying) -- Primary email address
    - email2 (character varying) -- Secondary personal email
    - nidn (character varying) -- National Lecturer Registry Number (NIDN) -- Presence indicates an official verified teaching academic
    - nuptk (character varying) -- Basic school teacher registry number
    - nira_serdos (character varying) -- Lecturer certification number (Serdos / Sertifikasi Dosen)
    - nira_bkd (character varying) -- BKD reporting sequence number
    - id_satker_struktural (character varying) -- Structural management unit key
    - id_struktural (integer) -- Structural position key
    - nama_jstruktural (character varying) -- Name of structural position held (e.g., 'Kepala Departemen', 'Dekan', 'Rektor')
    - jenis_struktural (character varying) -- Structural position type description
    - level_jstruktural (smallint) -- Structural level index
    - nilai_jstruktural (integer) -- Structural rank score
    - tmt_struktural (timestamp without time zone) -- TMT date for structural management position
    - tmt_akhir_struktural (timestamp without time zone) -- Structural end date
    - tst_struktural (timestamp without time zone) -- Structural safety date
    - is_struktural_plt (smallint) -- 1 if acting/PLT head position, 0 for permanent appointments
    - id_satker_struktural_2 (character varying) -- Secondary structural management unit key
    - id_struktural_2 (integer) -- Secondary structural position key
    - nama_jstruktural_2 (character varying) -- Secondary structural position name
    - jenis_struktural_2 (character varying) -- Secondary structural type
    - level_jstruktural_2 (smallint) -- Secondary level index
    - nilai_jstruktural_2 (integer) -- Secondary score mapping
    - tmt_struktural_2 (timestamp without time zone) -- Secondary TMT date
    - tmt_akhir_struktural_2 (timestamp without time zone) -- Secondary end date
    - tst_struktural_2 (timestamp without time zone) -- Secondary safety date
    - is_struktural_plt_2 (smallint) -- 1 if secondary PLT head position, 0 for permanent appointments
    - no_sertifikasi (character varying) -- National professional certificate number
    - tgl_sertifikasi (timestamp without time zone) -- Date professional certification was issued
    - gelar_depan (character varying) -- Titles preceding name (e.g., 'Prof.', 'Dr.', 'Ir.')
    - gelar_depan_2 (character varying) -- Secondary prefix title
    - gelar_belakang (character varying) -- Titles trailing name (e.g., 'S.T.', 'M.T.', 'Ph.D.')
    - gelar_belakang_2 (character varying) -- Secondary suffix title
    - gelar_prof (character varying) -- Professor academic title string
    - tgl_pensiun (timestamp without time zone) -- Projected retirement date of employee
    - tmt_cpns (timestamp without time zone) -- Date employee was appointed Candidate Civil Servant
    - tmt_non_cpns (timestamp without time zone) -- Candidate Non-PNS start date
    - tmt_pns (timestamp without time zone) -- Date employee was appointed Permanent Civil Servant (PNS)
    - tmt_non_pns (timestamp without time zone) -- Permanent Non-PNS start date
    - tmt_honorer (integer) -- Start year as casual worker
    - golongan (character varying) -- Civil service rank scale group (e.g., 'III/a', 'IV/a', 'IV/b', 'IV/c')
    - namapangkat (character varying) -- Civil service rank name (e.g., 'Penata Muda', 'Pembina', 'Guru Besar')
    - tmt_pangkat (timestamp without time zone) -- Pangkat scale TMT date
    - nama_jenis_pangkat (character varying) -- Pangkat scale classification
    - pendidikan_versi_kepegawaian (character varying) -- Degrees tracked by Kepegawaian HR
    - pendidikan_status_versi_kepegawaian (character varying) -- Kepegawaian validation status
    - pendidikan_bidang_versi_kepegawaian (character varying) -- HR field track
    - nama_institusi_versi_kepegawaian (character varying) -- HR university name
    - negara_institusi_versi_kepegawaian (character varying) -- HR university country
    - pendidikan_tertinggi (character varying) -- Student education degree completed: 'Sarjana' (Bachelor), 'Master' (Master), 'Doktor' (Doctoral/PhD), 'Diploma Tiga' (Diploma)
    - pendidikan_status (character varying) -- Degree status: 'S1' (Bachelor), 'S2' (Master), 'S3' (Doctoral/PhD), 'D1' (Diploma), ...
    - pendidikan_bidang (character varying) -- Major field of study concentration
    - nama_institusi (character varying) -- Academic institution where highest degree was earned (e.g., 'ITS', 'UI', 'ITB', '海外大学' / overseas uni)
    - negara_institusi (character varying) -- Country of highest degree (e.g., 'Indonesia', 'Jepang', 'Amerika Serikat')
    - id_scopus (character varying) -- Researcher Scopus ID (presence indicates active international research publishing profiles)
    - id_sinta (character varying) -- National Sinta researcher portal ID (presence indicates active national research profiles)
    - id_lab (character varying) -- Head laboratory identifier major mapping
    - sso_id (character varying) -- Active LDAP/SSO user handle
    - finger_id (integer) -- Biometric attendance device ID
    - has_nonpns (integer) -- 1 if staff has permanent nonpns history
    - id (integer) -- Internal sequence key
    - version (integer) -- Record version tracker"""
        
        # Keywords that trigger the Student table
        student_keywords = ["student", "students", "mahasiswa", "mhs"]
        if any(keyword in q_lower for keyword in student_keywords):
            # Only add it if Chroma didn't already find it
            if "akademik.dim_mahasiswa" not in schema_context:
                schema_context += "\n\n" + schema_dim_mahasiswa
                print("⚡ [FORCE INJECT] Added 'akademik.dim_mahasiswa' based on keywords.")

        # Keywords that trigger the Teacher table
        teacher_keywords = ["teacher", "teachers", "dosen", "staff", "pegawai"]
        if any(keyword in q_lower for keyword in teacher_keywords):
            # Only add it if Chroma didn't already find it
            if "kepegawaian.dim_pegawai" not in schema_context:
                schema_context += "\n\n" + schema_dim_pegawai
                print("⚡ [FORCE INJECT] Added 'kepegawaian.dim_pegawai' based on keywords.")

        # 4. Synthesize the main LLM Prompt
        prompt = (
            f"You are a precise, zero-hallucination PostgreSQL expert database translator.\n"
            f"Review the provided database layout options and select the appropriate columns to answer the user request.\n\n"
            f"Database Structural Options:\n"
            f"{schema_context}\n\n"
            f"EXACT SQL TEMPLATES (CRITICAL):\n"
            f"If the user asks for the 'number of students/mahasiswa in a certain department through the years X to Y', you MUST mimic this exact structure, replacing the years and the 'jurusan' (department) string dynamically. Use UNION ALL for each year requested:\n"
            f"```sql\n"
            f"SELECT '2022' AS tahun, COUNT(*) AS jumlah_mahasiswa\n"
            f"FROM akademik.dim_mahasiswa AS m\n"
            f"WHERE m.nama_departemen ILIKE '%Teknik Informatika%'\n"
            f"AND m.tahun_masuk <= 2022\n"
            f"AND (m.tahun_keluar IS NULL OR m.tahun_keluar >= 2022)\n"
            f"UNION ALL\n"
            f"SELECT '2023' AS tahun, COUNT(*) AS jumlah_mahasiswa\n"
            f"FROM akademik.dim_mahasiswa AS m\n"
            f"WHERE m.nama_departemen ILIKE '%Teknik Informatika%'\n"
            f"AND m.tahun_masuk <= 2023\n"
            f"AND (m.tahun_keluar IS NULL OR m.tahun_keluar >= 2023)\n"
            f"UNION ALL\n"
            f"SELECT '2024' AS tahun, COUNT(*) AS jumlah_mahasiswa\n"
            f"FROM akademik.dim_mahasiswa AS m\n"
            f"WHERE m.nama_departemen ILIKE '%Teknik Informatika%'\n"
            f"AND m.tahun_masuk <= 2024\n"
            f"AND (m.tahun_keluar IS NULL OR m.tahun_keluar >= 2024)\n"
            f"ORDER BY tahun\n"
            f"```\n\n"
            f"If the user asks for the 'number of teachers/dosen in a certain department through the years X to Y', you MUST mimic this exact structure, replacing the years and the 'jurusan' (department) string dynamically. Use UNION ALL for each year requested:\n"
            f"```sql\n"
            f"SELECT '2023' AS tahun, COUNT(*) AS jumlah_dosen\n"
            f"FROM kepegawaian.dim_pegawai AS dp\n"
            f"WHERE dp.jenis_pegawai = 'Dosen'\n"
            f"AND dp.status_aktif_simple = 'IN'\n"
            f"AND (dp.tanggal_keluar IS NULL OR dp.tanggal_keluar >= '2023-01-01')\n"
            f"AND dp.tanggal_masuk <= '2023-12-31'\n"
            f"AND dp.jurusan ILIKE '%Informatika%'\n"
            f"UNION ALL\n"
            f"SELECT '2024' AS tahun, COUNT(*) AS jumlah_dosen\n"
            f"FROM kepegawaian.dim_pegawai AS dp\n"
            f"WHERE dp.jenis_pegawai = 'Dosen'\n"
            f"AND dp.status_aktif_simple = 'IN'\n"
            f"AND (dp.tanggal_keluar IS NULL OR dp.tanggal_keluar >= '2024-01-01')\n"
            f"AND dp.tanggal_masuk <= '2024-12-31'\n"
            f"AND dp.jurusan ILIKE '%Informatika%'\n"
            f"```\n\n"
            f"Task: Convert this request into a clean PostgreSQL query string: {question}\n\n"
            f"CRITICAL SYSTEM RULES:\n"
            f"1. SCHEMA-GROUNDED VALIDATION (ANTI-HALLUCINATION):\n"
            f"   - Carefully inspect the tables and columns available in the Database Structural Options above.\n"
            f"   - If the user asks for concepts, entities, or fields that are NOT present in the schema context,\n"
            f"     you MUST NOT generate a SQL query. Do not fallback to selecting random columns.\n"
            f"   - If the requested data is missing, you MUST output exactly this message as raw text (no markdown, no code blocks):\n"
            f"     I apologize, but the academic data warehouse currently only contains student profiles, aggregate enrollment statistics, and employment histories.\n\n"
            f"2. You MUST prefix every table name with its schema prefix (e.g., 'akademik.dim_mahasiswa').\n"
            f"3. TABLE ALIASING & COLUMN PREFIXING (CRITICAL FOR POSTGRES):\n"
            f"   - ALWAYS assign a short, distinct table alias in the FROM or JOIN clause (e.g., 'kepegawaian.statis_riwayat_status_pegawai AS s').\n"
            f"   - Prefix every column name in your SELECT and WHERE clauses with its respective table alias (e.g., 's.nip', 's.status_pegawai').\n"
            f"   - NEVER prefix columns with just a schema name (e.g., write 's.nama_status_aktif_pegawai', NEVER 'kepegawaian.nama_status_aktif_pegawai'). This prevents PostgreSQL syntax and resolution errors.\n"
            f"4. DEDUPLICATION & ORDER BY RULE (CRITICAL FOR POSTGRES):\n"
            f"   - Use the `DISTINCT` keyword for lists/all options queries to avoid duplicate rows.\n"
            f"   - Whenever using `SELECT DISTINCT`, any column in the `ORDER BY` clause MUST also be present in the `SELECT` list (e.g., write `SELECT DISTINCT mhs.nama ... ORDER BY mhs.nama` or `SELECT DISTINCT mhs.id, mhs.nama ... ORDER BY mhs.id`). NEVER order by a column that is not in the `SELECT` clause when using `DISTINCT`.\n"
            f"5. FUZZY TEXT MATCHING (CRITICAL): When filtering by text or string columns (e.g., jobs, cities, names), ALWAYS use PostgreSQL's case-insensitive `ILIKE '%keyword%'` operator instead of exact `=` matches. Data often contains compound values (e.g., 'Petani/ nelayan' or 'S1 Teknik'), so using `ILIKE '%Petani%'` ensures you do not miss records.\n"
            f"6. Whenever necessary, use 'WHERE' keyword to cross search from the tables needed.\n"
            f"7. OUTPUT FORMAT:\n"
            f"   - If answerable: Output ONLY the raw executable SQL inside a markdown block: ```sql\\nSELECT ...\\n```\n"
            f"   - If unanswerable: Output ONLY the exact apology sentence as plain text (no markdown, no blocks).\n"
            f"8. Do not write explanations, introductions, or warnings. Output ONLY the code block or apology text as directed."
            f"8. EXACT TABLE NAME FIDELITY (CRITICAL):\n"
            f"   - Copy table names CHARACTER-FOR-CHARACTER from the schema context provided above.\n"
            f"   - Do NOT abbreviate, drop letters, or modify long table names (e.g., write 'statis_aggr_lintas_periode_penyematan_status_mahasiswa', NEVER truncate or alter words like 'penyematan').\n"
        )

        print("\n" + "="*60)
        print(" 🔥 [LIVE STREAM DEBUGGER] OLLAMA IS EXAMINING RE-RANKED BLUEPRINTS:")
        print("="*60)

        raw_content = ""
        try:
            response_stream = ollama_client.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}], stream=True)
            for chunk in response_stream:
                token = chunk["message"]["content"]
                raw_content += token
                print(token, end="", flush=True)
        except Exception as e:
            print(f"\n🚨 [OLLAMA ENGINE CRASH]: {e}")

        print("\n" + "="*60)

        # Extract code from markdown block
        print("raw_content: ",raw_content) #debug
        sql = raw_content.strip()
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        # Sanitize query comments
        sql = re.sub(re.compile(r"--.*?\n"), "", sql + "\n")
        sql = re.sub(re.compile(r"--.*?$"), "", sql)

        sql = re.sub(r';\s*(?=(ORDER BY|GROUP BY|LIMIT|HAVING))', ' ', sql, flags=re.IGNORECASE)
        sql = " ".join(sql.split()).strip()

        end_time=datetime.now(timezone.utc)
        print(end_time)
        elapsed_time=end_time-start_time
        print(f"Elapsed Time for the request: {elapsed_time}")
        return sql
   
    def run_sql(self, sql):
        if not self.conn: 
            raise Exception("Database connection is missing!")
        return pd.read_sql_query(sql, self.conn)


# --- 2. INITIALIZE GLOBAL SERVICES ---
# Timeout configurations to protect slow model generation steps on local CPU
ollama_client = Client(host='http://127.0.0.1:11434', timeout=1800.0)

# Instantiate and configure Vanna to point to the specific university DW
vn = MyPrivateVanna(model_name="qwen3.5:9b")
vn.connect_to_postgres(host="10.199.16.221", dbname="itsdw", user="ai_llm", password="!Donald_Babatan57")


# --- 3. UNIFIED CHAT API ENDPOINT ---
query_cache = {}

@app.route('/ask-ai', methods=['POST'])
def ask_ai():
    try:
        payload = request.get_json()
        chat_history = payload.get("history", [])

        session_id = payload.get("session_id") or str(uuid.uuid4())
        
        if not chat_history:
            return jsonify({"error": "No prompt history found."}), 400

        # Extract the user's latest message
        start_time2=datetime.utcnow()
        user_question = chat_history[-1]["content"]
        current_user = chat_history[-1]["user"]
        print(f"\n[SERVER API]: Processing database question: '{user_question}'")

        # 1. Pipeline Action: Turn text to clean SQL using offline translation + Vector match + Re-ranker
        sql_query = vn.generate_sql(user_question)
        print(f"[SERVER API]: Resulting SQL Statement -> {sql_query}")

        #Rejection layer if pipeline is not able to answer query
        is_rejection = (
            "apologize" in sql_query.lower() or 
            "not loaded" in sql_query.lower() or 
            "sorry" in sql_query.lower() or 
            not sql_query.strip().upper().startswith("SELECT")
        )
        records = []
        query_id = str(uuid.uuid4())

        if is_rejection:
            # Bypass PostgreSQL and set the response immediately to avoid syntax crashes!
            is_refusal = True
            ai_reply = "I apologize, but the academic data warehouse currently only contains student profiles, aggregate enrollment statistics, and employment histories. Specific transactional data regarding individual course listings, classes, and instructors is not loaded into the system yet, so I cannot answer this query."
            print("[SERVER API]: Rejection triggered. PostgreSQL execution bypassed successfully!")

        else:
            # 2. Pipeline Action: Execute query on the Postgres database connection
            df = vn.run_sql(sql_query)

            # Convert DataFrame results to serialized JSON records
            records = []
            if df is not None:
                query_cache[query_id] = df

                json_string = df.head(10).to_json(orient="records", date_format="iso")
                records = json.loads(json_string)

            end_time2=datetime.utcnow()
            elapsed_time2=end_time2-start_time2

            # 3. Structure Assistant Reply (Markdown format with syntax block tags)
            ai_reply = f"**Time for processing question: {elapsed_time}**\n**Generated SQL Query:**\n```sql\n{sql_query}\n```\n\n**Query Database Results:**\n"
            if len(records) == 0:
                ai_reply += "No matching records found for this database query."
            else:
                ai_reply += f"Query executed successfully. Displaying **{len(records)}** row(s) below."
                print("records: ",records)

        # Handles the firestore collections writing
        # 1. Append the assistant's new response to the local chat history list
        updated_history = list(chat_history)
        updated_history.append({ "role": "assistant", "content": ai_reply, "result_table_in_json": records, "query_id": query_id })

        # 2. Add these lines to write to Firestore
        if db is not None:
            # Generate a clean short title from the first question
            session_title = chat_history[0]["content"] if len(chat_history) > 0 else user_question
            if len(session_title) > 40:
                session_title = session_title[:37] + "..."

            # THIS is the part that implicitly creates the collection and document
            session_ref = db.collection("users").document(current_user).collection("chat_sessions").document(session_id)
            session_ref.set({
                "session_id": session_id,
                "title": session_title,
                "updated_at": datetime.now(timezone.utc),
                "history": updated_history
            })
            print(f"[SERVER]: Syncing session {session_id} to Firestore.")

        return jsonify({
            "message": {
                "role": "assistant",
                "content": ai_reply,
                "query_id": query_id,
                "raw_data": records
            },
            "session_id": session_id
        })
        
        

    except Exception as e:
        print(f"[PIPELINE ERROR DETECTED]: {str(e)}")

        return jsonify({
            "error": "Failed to complete AI database pipeline transaction",
            "details": str(e)
        }), 500

@app.route('/download-csv', methods=['GET'])
def download_csv():
    try:
        # 1. Grab the unique query cache ID from the URL parameters (?id=...)
        query_id = request.args.get('id')
        if not query_id:
            return jsonify({"error": "No query ID provided."}), 400
        
        # Safely bind to the global query_cache dictionary defined at the top of your server file
        global query_cache

        print(f"\n[SERVER CSV DOWNLOAD]: Retrieving dataset reference [{query_id}] from in-memory cache...")
        
        # 2. Retrieve the pre-computed DataFrame from cache to avoid hitting the database again
        if query_id not in query_cache:
            return jsonify({"error": "Cached dataset has expired or was not found. Please re-run your prompt query."}), 404

        df=query_cache[query_id]
            
        # Convert DataFrame to a raw CSV format
        csv_data = df.to_csv(index=False)
        
        # Return CSV file with attachment headers to trigger the browser's download prompt
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-disposition": f'attachment; filename="results_{query_id[:8]}.csv"',
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        print(f"[CSV DOWNLOAD ERROR]: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Running on local loopback interface (Port 5050) to route traffic from HTML frontend
    app.run(host='0.0.0.0', port=5050, debug=True)
