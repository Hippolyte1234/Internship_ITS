import os
import chromadb

# Determine the absolute directory path where your files reside
current_dir = os.path.dirname(os.path.abspath(__file__)) or os.getcwd()
db_path = os.path.join(current_dir, "vanna_knowledge_base")

print(f"[TRAINING] Connecting absolutely to ChromaDB at: {db_path}")

try:
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection("vanna_collection")

    # --- 1. ACADEMIC SCHEMA (11 TABLES) ---
    dim_periode_def = """Database Table Definition Asset:
Table: akademik.dim_periode
Description: Stores records of official academic calendar periods, semesters, and active academic years at the university.
Columns:
  - id (integer) -- Internal sequence key
  - id_periode (character varying) -- Unique business identifier
  - nama_periode (character varying) -- Textual name (e.g., '2024/2025 Ganjil', '2023/2024 Genap')
  - semester (integer) -- Numeric semester indicator: 1 = Ganjil (Odd/Fall), 2 = Genap (Even/Spring), 3 = Pendek (Short/Summer term)
  - is_periode_aktif (integer) -- Active period flag: 1 = Currently Active and ongoing semester, 0 = Historic completed semester
  - tanggal_mulai (date) -- Official start date of classes
  - tanggal_selesai (date) -- Official end date of semester classes and exams
  - kode_periode (character varying) -- Semester year code (e.g., '20241' for 2024/2025 Ganjil, '20242' for 2024/2025 Genap)
  - kode_tahun_ajaran (character varying) -- Annual year group (e.g., '2024')
  - nama_tahun_ajaran (character varying) -- Full year range text (e.g., '2024/2025')
  - version (integer) -- Record version tracker
  - start_date (date) -- System start validity date
  - expired_date (date) -- System end validity date
Semantic Keywords & Translation Encodings: periode aktif, semester ganjil, semester genap, tahun ajaran baru, tanggal mulai kuliah, kalender universitas, masa studi resmi, ganjil genap, odd semester, even semester, active academic year, start date, end date, academic calendar"""

    dim_mahasiswa_def = """Database Table Definition Asset:
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
  - start_date (timestamp without time zone) -- Record valid from
  - expired_date (timestamp without time zone) -- Record expired on
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
  - is_asing (integer) -- 1 if student is a foreign national, 0 for Indonesian citizens
Semantic Keywords & Translation Encodings: Mahasiswa, NIM, NRP, Tanggal Lahir, Jenis Kelamin, Kota Asal, Domisili SLTA, Pekerjaan Orang Tua, Gaji Bapak, Gaji Ibu, Ibu Rumah Tangga, Wali Hukum, Saudara Kakak Adik, Fakultas, Program Studi, Jurusan, Bidang Studi, Tahun Masuk, Angkatan, Lulus Sarjana, S1, S2, S3, D3, D4, Wisuda, Tugas Akhir, Skripsi, SNBP, SNBT, Mandiri, IUP, Asing, Student, NR, GPA, Batch, Enrollment Year"""

    dim_status_keaktifan_mahasiswa_def = """Database Table Definition Asset:
Table: akademik.dim_status_keaktifan_mahasiswa
Description: Metadata table classifying the different operational statuses a student can have during a semester.
Columns:
  - id (integer) -- Sequence key
  - kode_status_aktif_mahasiswa (character varying) -- Single-character status code (e.g., 'N' = Aktif, 'C' = Cuti/Leave, 'D' = Dispensasi, 'T' = Non Aktif, 'S' = Skorsing)
  - nama_status_aktif_mahasiswa (character varying) -- Textual state description ('Aktif', 'Cuti', 'Non Aktif, 'Dispensasi', 'Skorsing')
  - id_status_mhs_itsdw (character varying) -- DW system key
  - kode_status_mhs_siakad (character varying) -- Academic application status code
  - start_date (date) -- Record valid from
  - expired_date (date) -- Record expired on
  - version (integer) -- Record version tracker
  - id_ref_status_mahasiswa_mdm (integer) -- Master data reference ID
  - nama_ref_status_mahasiswa_mdm (character varying) -- Master data reference description
  - kode_ref_status_mahasiswa_mdm (character varying) -- Master data code
Semantic Keywords & Translation Encodings: status mahasiswa, keaktifan mhs, nama status aktif, kode referensi, cuti belajar, drop out, lulus kuliah, berhenti studi, skorsing, alumnus, active state, leave of absence, graduated, withdrawn"""

    fact_penyematan_status_mahasiswa_def = """Database Table Definition Asset:
Table: akademik.fact_penyematan_status_mahasiswa
Description: Core transactional fact table tracking student academic performances, GPA (IPK), semester GPA (IPS), and SKS credits per semester period.
Columns:
  - dim_periode_id (bigint) -- FK linking to akademik.dim_periode
  - dim_mahasiswa_id (bigint) -- FK linking to akademik.dim_mahasiswa
  - dim_status_keaktifan_mahasiswa_id (integer) -- FK linking to akademik.dim_status_keaktifan_mahasiswa
  - dim_jenis_keluar_mahasiswa_id (integer) -- FK linking to akademik.dim_jenis_keluar_mahasiswa
  - jumlah (text) -- Headcount metrics string
  - updated_at (timestamp without time zone) -- Last modification log
  - semester_ke (integer) -- The ordinal semester number the student is currently in (e.g., 1, 2, 3, 4, 5, 6, 7, 8)
  - ips (double precision) -- Index Prestasi Semester (IPS) representing the student's GPA for this single specific period (0.00 to 4.00)
  - sks_diambil (integer) -- SKS (Credits) taken during this specific active semester (usually 0 to 24 SKS)
  - ipk (double precision) -- Index Prestasi Kumulatif (IPK) representing the total cumulative GPA across all completed semesters (0.00 to 4.00)
  - sks_total (integer) -- Total accumulated SKS (credits) successfully passed by the student since their first semester
  - record_status (character varying) -- Operational state
  - deleted_at (character varying) -- Deletion audit
  - archive_at (character varying) -- Archive audit
  - status_reason (character varying) -- Administrative remarks
  - status_updated_at (timestamp without time zone) -- Change timestamp
Semantic Keywords & Translation Encodings: status mahasiswa aktif, riwayat tidak aktif, IPK kumulatif, IPS semester, SKS total, SKS diambil, semester berjalan, periode akademik, data cuti belajar, semester ke, Cumulative GPA, Credit Load, Semester GPA"""

    dim_jenis_keluar_mahasiswa_def = """Database Table Definition Asset:
Table: akademik.dim_jenis_keluar_mahasiswa
Description: Dimension mapping all pathways and classifications under which a student departs or graduates from the university.
Columns:
  - id (integer) -- Primary key : Internal sequence identifier
  - kode_jenis_keluar_mahasiswa (character varying) -- Output code (e.g., 'L' = Lulus, 'M' = Mutasi, 'U' = Mengundurkan Diri, 'W' = Meninggal)
  - nama_jenis_keluar_mahasiswa (character varying) -- Textual exit type description ('Lulus', 'Mutasi', 'Mengundurkan Diri', 'Meninggal')
  - id_status_mhs_itsdw (character varying) -- DW system key
  - start_date (date) -- Record valid from
  - expired_date (date) -- Record expired on
Semantic Keywords & Translation Encodings: Lulus sarjana, Cut off akademik, Drop out mahasiswa, Transfer program studi, Pindah kampus lain, Status wisuda resmi, Ijazah terakhir, Skripsi sidang akhir, Tidak lulus ujian, Cutoff SPP mahasiswa, Alumni terdaftar aktif, Riwayat status mhs, graduation, drop out, resigned, transfer"""

    statis_aggr_penyematan_status_mahasiswa_def = """Database Table Definition Asset:
Table: akademik.statis_aggr_penyematan_status_mahasiswa
Description: Pre-computed, aggregated historical snapshot table storing total headcount counts of students, sliced by period, faculty, department, and active status.
Columns:
  - dim_periode_id (bigint) -- FK linking to akademik.dim_periode
  - kode_periode (character varying) -- Semester code (e.g., '20241')
  - nama_fakultas (character varying) -- Name of the faculty (e.g., 'FTEIC', 'FTIK')
  - nama_departemen (character varying) -- Name of parent department
  - nama_prodi (character varying) -- Name of study major program and its degree level (e.g., 'S1 Teknik Informatika', ' S4 Sistem Informasi')
  - nama_bidang_studi (character varying) -- Specific academic major concentration track
  - id_status (bigint) -- FK linking to akademik.dim_status_keaktifan_mahasiswa.id
  - nama_status (character varying) -- Academic status description (e.g., 'Aktif', 'Cuti', 'Lulus', 'Keluar')
  - jenis_status (text) -- Broad status group : 'IN' or 'OUT'
  - jumlah (bigint) -- Total aggregate headcount of students in this group (Use SUM(jumlah) to calculate total enrollment)
  - dim_waktu_snapshot_id (integer) -- Snapshot date key
  - tanggal_snapshot (date) -- Date this aggregate count was locked
  - created_at (timestamp with time zone) -- Timestamp of record insertion
Semantic Keywords & Translation Encodings: statistik mahasiswa, jumlah siswa, status akademik, fakultas, program studi, prodi, departemen, total registrasi, rekapitulasi kelas, enrollment headcount, aggregate student counts, major department stats"""

    statis_penyematan_status_mahasiswa_def = """Database Table Definition Asset:
Table: akademik.statis_penyematan_status_mahasiswa
Description: Comprehensive snapshot table capturing every individual student's status, GPA (IPK), semester GPA (IPS), and SKS credits at specific snapshot points in time. Highly useful for historical reporting.
Columns:
  - dim_periode_id (bigint) -- FK linking to akademik.dim_periode
  - kode_periode (character varying) -- Academic semester code (e.g., '20241')
  - dim_mahasiswa_id (bigint) -- FK linking to akademik.dim_mahasiswa
  - nim (character varying) -- Student identification number / NRP
  - nama_mahasiswa (character varying) -- Student's full name
  - dim_status_keaktifan_mahasiswa_id (integer) -- FK linking to akademik.dim_status_keaktifan_mahasiswa
  - nama_status_aktif_mahasiswa (character varying) -- Academic status description ('Aktif', 'Cuti', 'Lulus', 'Drop Out')
  - dim_jenis_keluar_mahasiswa_id (integer) -- FK linking to akademik.dim_jenis_keluar_mahasiswa
  - nama_jenis_keluar_mahasiswa (character varying) -- Path of exit
  - semester_ke (integer) -- Ordinal semester number the student was in (e.g., 1, 2, 3, 4, 5, 6, 7, 8)
  - ips (double precision) -- Index Prestasi Semester (IPS) representing GPA for this specific period
  - sks_diambil (integer) -- SKS (Credits) taken during this specific snapshot semester
  - ipk (double precision) -- Index Prestasi Kumulatif (IPK) representing total cumulative GPA up to this point
  - sks_total (integer) -- Cumulative SKS passed up to this snapshot date
  - jumlah (text) -- Metric count helper
  - dim_waktu_snapshot_id (integer) -- Snapshot time key
  - tanggal_snapshot (date) -- Date this snapshot was recorded
  - created_at (timestamp with time zone) -- Timestamp of snapshot generation
  - nama_fakultas (character varying) -- Student's faculty name at snapshot point
  - nama_departemen (character varying) -- Student's department name at snapshot point
  - nama_prodi (character varying) -- Student's study program name with its degree level(e.g., 'S1 Sistem Informasi', 'S2 Teknik Informatika')
  - nama_bidang_studi (character varying) -- Major concentration
Semantic Keywords & Translation Encodings: mahasiswa NIM, nama lengkap, status aktif, lulus, wisuda, cuti belajar, IPK, SKS total, semester berjalan, prodi, jurusan, fakultas, snapshot, IPK rata-rata, SKS diambil, Student GPA list, cumulative credit stats"""

    statis_aggr_lintas_periode_penyematan_status_mahasiswa_def = """Database Table Definition Asset:
Table: akademik.statis_aggr_lintas_periode_penyematan_status_mahasiswa
Description: Aggregated historical table tracking student enrollment distributions across multiple periods (lintas periode) for trend analysis.
Columns:
  - dim_periode_id (bigint) -- FK linking to akademik.dim_periode
  - kode_periode (character varying) -- Academic period code (e.g., '20231', '20241')
  - nama_fakultas (character varying) -- Faculty name
  - nama_departemen (character varying) -- Parent department
  - nama_prodi (character varying) -- Study program major name with its degree level (e.g., 'S1 Sistem Informasi', 'S2 Teknik Informatika')
  - nama_bidang_studi (character varying) -- Major concentration track
  - id_status (bigint) -- FK linking to akademik.dim_status_keaktifan_mahasiswa.id
  - nama_status (character varying) -- Academic status description ('Aktif', 'Cuti', 'Lulus', 'DO')
  - jenis_status (text) -- Broad status group : 'IN' or 'OUT'
  - jumlah (bigint) -- Total aggregate headcount in this specific group (Use SUM(jumlah) to calculate total trends)
  - dim_waktu_snapshot_id (integer) -- Snapshot time key
  - tanggal_snapshot (date) -- Snapshot date
  - created_at (timestamp with time zone) -- Record creation timestamp
Semantic Keywords & Translation Encodings: fakultas, departemen, prodi, riwayat akademik, cuti, drop out, lulus, beasiswa, lintas periode, perkembangan tahunan, historical enrollment trends, cross period student stats"""

    dim_bidang_studi_def = """Database Table Definition Asset:
Table: akademik.dim_bidang_studi
Description: Master directory of all academic programs, study tracks, concentrations, and majors configured at the university.
Columns:
  - id (integer) -- Sequence key
  - id_bidang_studi (character varying) -- Unique business key for study field
  - nama_bidang_studi (character varying) -- Name of study field major concentration
  - jenjang_pendidikan (character varying) -- Degree level: 'S1' (Bachelor), 'S2' (Master), 'S3' (Doctoral), 'D3' (Diploma III), 'D4' (Diploma IV)
  - nama_prodi (character varying) -- Major study program (e.g., 'S1 Teknik Informatika', 'S2 Teknik Mesin')
  - nama_departemen (character varying) -- Parent department name (e.g., 'Departemen Informatika')
  - nama_fakultas (character varying) -- Parent faculty name
  - kodeprodi_siakad (character varying) -- Siakad app code
  - id_bidang_studi_itsdw (integer) -- DW internal map key
  - kode_satker_prodi_mdm (character varying) -- Satker MDM mapping key
  - start_date (date) -- Validity start
  - expired_date (date) -- Validity expiration
  - kode_satker_departemen_mdm (character varying) -- Parent department code
  - kode_satker_fakultas_mdm (character varying) -- Parent faculty code
  - nama_pendek_fakultas (character varying) -- Shortened faculty name
  - id_prodi_itsdw (integer) -- Study program DW key
Semantic Keywords & Translation Encodings: Jurusan, Prodi, Fakultas, Daftar jurusan, Kode prodi, Jenjang pendidikan, S1, S2, S3, Diploma, Sarjana, Program studi, Nama bidang studi, major list, study program directory"""

    statis_bidang_studi_def = """Database Table Definition Asset:
Table: akademik.statis_bidang_studi
Description: Historical snapshot table summarizing headcount aggregates per major concentration program at defined snapshot points.
Columns:
  - dim_bidang_studi_id (integer) -- FK linking to akademik.dim_bidang_studi
  - kode_bidang_studi (text) -- Major identifier code
  - nama_bidang_studi (text) -- Name of study track major with its degree level
  - jenjang_pendidikan (text) -- Degree level ('S1', 'S2', 'S3', 'D3', 'D4')
  - nama_prodi (text) -- Major study program name
  - nama_departemen (text) -- Parent department name
  - nama_fakultas (text) -- Parent faculty name
  - jumlah (integer) -- Metrics count helper
  - dim_waktu_snapshot_id (integer) -- Snapshot date key
  - tanggal_snapshot (date) -- Snapshot date
  - created_at (timestamp with time zone) -- Timestamp of record insertion
Semantic Keywords & Translation Encodings: Jurusan, Program Studi, Prodi, Fakultas, Departemen, Bidang Studi, Jenjang Pendidikan, Sarjana, Diploma, Jumlah Mahasiswa, Statistik Akademik, major concentration headcount, active enrollment counts"""

    rep_perbandingan_jumlah_mahasiswa_lintas_periode_def = """Database Table Definition Asset:
Table: akademik.rep_perbandingan_jumlah_mahasiswa_lintas_periode
Description: Statistical report table tracking number of students, the difference, delta, and percentage changes in student enrollment counts from the current period compared to previous periods.
Columns:
  - tanggal_snapshot (date) -- Date this comparative record was compiled
  - kode_periode (text) -- Academic period code (e.g., '20241')
  - total_now (numeric) -- Total student headcount registered in current period
  - total_prev (numeric) -- Total student headcount registered in previous comparative period
  - delta (numeric) -- Net change in headcount (total_now - total_prev)
  - pct_change (numeric) -- Percentage change value representing growth or decline (e.g., positive value for growth, negative for drop)
Semantic Keywords & Translation Encodings: Jumlah mahasiswa, total saat ini, banding periode lalu, selisih angka, persentase naik turun, tren pertumbuhan mhs, laporan akademik statistik, perkembangan siswa, kode semester tahun, analisis lintas waktu, enrollment comparison metrics, pct_change, delta, growth rate"""


    # --- 2. HR KEPEGAWAIAN SCHEMA (7 TABLES) ---
    dim_pegawai_def = """Database Table Definition Asset:
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
  - version (integer) -- Record version tracker
  - start_date (timestamp without time zone) -- Validity start date
  - expired_date (timestamp without time zone) -- Validity end date
Semantic Keywords & Translation Encodings: dosen, pengajar, guru, lecturer, teacher, staf akademik pengajar, data dosen, NIDN, serdos, pegawai, karyawan, status dosen aktif, daftar pendidik, tenaga fungsional pengajar, civitas akademika dosen, NIP, Nomor Pokok Pegawai, Nama Staff, Karyawan Tetap, Status Aktif, S1, S2, S3, Scopus, Sinta, Professor, Asisten Ahli, Lektor, PNS, Lecturer directory, staff email lists"""

    dim_satuan_kerja_def = """Database Table Definition Asset:
Table: kepegawaian.dim_satuan_kerja
Description: Structural hierarchy table mapping all organizational units, administrative departments, sections, centers, laboratories, and study program centers.
Columns:
  - id_satker (character varying) -- Administrative satker code/key
  - nama_satker (character varying) -- Name of unit (e.g., 'Fakultas Teknologi Elektro', 'Departemen Informatika')
  - parent_kode_satker (character varying) -- Code of parent reporting unit
  - kode_jenis_unit_kerja (character varying) -- Unit type code
  - nama_jenis_unit_kerja (character varying) -- Unit type description ('Program Studi', 'Unit Kerja', 'Fakultas', 'Jurusan', 'Laboratorium')
  - level (integer) -- Level from 1 to 5
  - tanggal_mulai_sk (timestamp without time zone) -- SK authorization start date
  - tahun_otk (integer) -- Organizational structure year code
  - jenjang_program_studi (text) -- Level under this satker (if satker is an academic program, e.g., 'S1', 'S2', 'S3')
  - id_satker_simpeg (character varying) -- Simpeg mapping key
  - id_satker_itsdw (character varying) -- DW internal key
  - id_prodi_pddikti (character varying) -- National PDDIKTI study program code
  - id_prodi_itsdw (character varying) -- DW program code
  - id_master_satuan_kerja_mdm (integer) -- MDM master record key
  - id_unit_organisasi_mihc (text) -- MIHC unit reference key
  - kode_level_0 (character varying) -- Level 0 structural identifier
  - nama_level_0 (character varying) -- Level 0 organization name (University level)
  - kode_level_1 (text) -- Level 1 structural identifier
  - nama_level_1 (text) -- Level 1 unit name (Faculty level)
  - kode_level_2 (text) -- Level 2 structural identifier
  - nama_level_2 (text) -- Level 2 unit name (Department level)
  - kode_level_3 (text) -- Level 3 structural identifier
  - nama_level_3 (text) -- Level 3 unit name (Study program level)
  - kode_level_4 (text) -- Level 4 structural identifier
  - nama_level_4 (text) -- Level 4 unit name (Section/Group level)
  - kode_level_5 (text) -- Level 5 structural identifier
  - nama_level_5 (text) -- Level 5 unit name (Unit level)
  - version (integer) -- Record version tracker
  - start_date (date) -- Validity start date
  - expired_date (date) -- Validity end date
  - id (integer) -- Sequence key
  - akreditasi_prodi (character varying) -- National accreditation score of study program (e.g., 'Unggul', 'Baik Sekali', 'Terakreditasi Semantara')
Semantic Keywords & Translation Encodings: satker, satuan kerja, unit organisasi, kode instansi, nama lembaga resmi, akreditasi prodi, Unggul, Baik, UPT, Biro, Dekanat, working unit directory, accreditation grade list"""

    dim_jenis_keluar_pegawai_def = """Database Table Definition Asset:
Table: kepegawaian.dim_jenis_keluar_pegawai
Description: Dimension mapping HR codes and pathways indicating why staff separate from active employment (resignation, retirement, contracts expired).
Columns:
  - id (bigint) -- Sequence key
  - start_date (timestamp without time zone) -- Validity start date
  - expired_date (timestamp without time zone) -- Validity end date
  - kode_jenis_keluar_pegawai (character varying) -- Separations code (e.g. 'P' for Pensium, 'B' for Berhenti Dengan Hormat, 'W' for Wafat)
  - nama_jenis_keluar_pegawai (character varying) -- Textual separation reason description (e.g., 'Pensiun' (Retired), 'Mengundurkan Diri' (Resigned), 'Kontrak Selesai' (Terminated), 'Wafat' (Deceased), 'Berhenti Dengan Hormat', 'Pindah')
  - id_status_peg_itsdw (integer) -- Legacy status index
  - id_ref_jenis_keluar_mdm (integer) -- MDM reference index
  - kode_ref_jenis_keluar_mdm (text) -- MDM reference code
  - nama_ref_jenis_keluar_mdm (text) -- MDM reference name
Semantic Keywords & Translation Encodings: alasan keluar pegawai, mutasi, pensiun, resignasi, mengundurkan diri, meninggal dunia, PHK, pemberhentian, termination reason, retired staff, resignation categories"""

    fact_riwayat_status_pegawai_def = """Database Table Definition Asset:
Table: kepegawaian.fact_riwayat_status_pegawai
Description: Core transactional fact table tracking staff exits, career changes, and active operational statuses across dates.
Columns:
  - dim_waktu_id (bigint) -- FK linking to public.dim_waktu
  - dim_pegawai_id (bigint) -- FK linking to kepegawaian.dim_pegawai
  - dim_status_keaktifan_pegawai_id (double precision) -- FK linking to kepegawaian.dim_status_keaktifan_pegawai
  - dim_jenis_keluar_pegawai_id (integer) -- FK linking to kepegawaian.dim_jenis_keluar_pegawai
  - jumlah (text) -- Metrics count helper string
  - updated_at (timestamp without time zone) -- Last modification log
  - record_status (character varying) -- Operational status : 'active' or 'deleted'
  - deleted_at (character varying) -- Deletion audit
  - status_reason (character varying) -- Reason text for administrative active status changes
  - status_updated_at (timestamp without time zone) -- Status timestamp
Semantic Keywords & Translation Encodings: Pegawai, Karyawan, Status Keaktifan, Jenis Keluar, Riwayat Pekerjaan, Alasan Perubahan, Pemutusan Kerja, Resign, Pensiun, Employee lifecycle metrics, HR fact records"""

    dim_status_keaktifan_pegawai_def = """Database Table Definition Asset:
Table: kepegawaian.dim_status_keaktifan_pegawai
Description: Dimension mapping all active and inactive career states an employee can be mapped to under HR registry policies.
Columns:
  - id (bigint) -- Primary sequence key
  - start_date (timestamp without time zone) -- Validity start date
  - expired_date (timestamp without time zone) -- Validity end date
  - kode_status_aktif_pegawai (text) -- HR active code (e.g., 'A' = Aktif, 'C' = Cuti, 'TB' = Tugas Belajar, 'DK' = Dipekerjakan)
  - nama_status_aktif_pegawai (text) -- Textual active state description ('Aktif', 'Dipekerjakan', 'Cuti Luar Tanggapan', 'Tugas Belajar')
  - id_status_peg_itsdw (integer) -- Legacy status index
  - id_ref_status_aktif_mdm (integer) -- MDM reference index
  - kode_ref_status_aktif_mdm (text) -- MDM reference code
  - nama_ref_status_aktif_mdm (text) -- MDM reference description
Semantic Keywords & Translation Encodings: status pegawai aktif, kondisi kerja non-aktif, data resign karyawan, cuti melahirkan, tugas belajar, active employment status list, staff active codes"""

    statis_riwayat_status_pegawai_def = """Database Table Definition Asset:
Table: kepegawaian.statis_riwayat_status_pegawai
Description: Detailed individual career status and demographic snapshot record for all employees at specific historical snapshot points in time. Highly useful for individual staff queries.
Columns:
  - dim_waktu_id (integer) -- FK linking to public.dim_waktu
  - tanggal (date) -- Snapshot date
  - nip (text) -- Student or Employee NIP / NRP registration number
  - nama_pegawai (text) -- Full name of employee
  - dim_status_keaktifan_pegawai_id (integer) -- FK linking to kepegawaian.dim_status_keaktifan_pegawai
  - nama_status_aktif_pegawai (text) -- Active status description ('Aktif', 'Tugas Belajar')
  - dim_jenis_keluar_pegawai_id (integer) -- FK linking to kepegawaian.dim_jenis_keluar_pegawai
  - nama_jenis_keluar_pegawai (text) -- Path of exit (if employee left during this period, e.g., 'Pensiun', 'Mengundurkan Diri')
  - jumlah (integer) -- Metrics count helper (value is 1)
  - dim_waktu_snapshot_id (integer) -- Snapshot time key
  - tanggal_snapshot (date) -- Date this snapshot record was compiled
  - created_at (timestamp with time zone) -- Timestamp of snapshot generation
  - id_satker (text) -- Working unit ID code
  - unit (text) -- Working unit name (e.g., 'Urusan Rumah Tangga', 'Departemen Informatika')
  - parent_unit (text) -- Parent structural unit name
  - parent_parent_unit (text) -- Parent-parent structural unit name
  - jenis_pegawai (text) -- Staff type description: 'Dosen' (Teachers/Faculty/Lecturers) or 'Tendik' (Support staff/Administrators)
  - status_pegawai (text) -- Employment status ('PNS', 'Non-PNS', 'Kontrak', 'Honorer')
  - pendidikan_tertinggi (text) -- Completed degree level completed ('Sarjana', 'Doktor', 'Magister', 'Diploma Dua', 'Diploma Tiga')
  - dim_pegawai_id (integer) -- FK linking to kepegawaian.dim_pegawai
Semantic Keywords & Translation Encodings: NIP, Nomor Pokok Pegawai, Nama Staff, Karyawan Tetap, Status Aktif, Cuti, Resign, Pensiun Dini, Tinggal Kerja, Unit Kerja, Jenjang Pendidikan S1 S2 S3, PNS Sipil, Kontrak, Honorer, Dosen, Tendik, individual employee snapshot history"""

    statis_aggr_riwayat_status_pegawai_def = """Database Table Definition Asset:
Table: kepegawaian.statis_aggr_riwayat_status_pegawai
Description: Pre-computed, aggregated historical snapshot table tracking total aggregate headcount counts of staff (teachers/dosen and administrators/tendik), sliced by period and department. Use for trend queries.
Columns:
  - dim_waktu_id (integer) -- FK linking to public.dim_waktu
  - tanggal (date) -- Snapshot date
  - id_satker (text) -- Working unit ID code
  - unit (text) -- Working unit name (e.g., 'Departemen Matematika')
  - parent_unit (text) -- Parent structural unit name
  - parent_parent_unit (text) -- Parent-parent structural unit name
  - id_status (bigint) -- FK linking to pegawai.dim_status_keaktifan_pegawai
  - nama_status (text) -- Active status description (e.g., 'Aktif', 'Tugas Belajar', 'Cuti di Luar Tanggungan Negara', 'Dipekerjakan')
  - jenis_status (text) -- Broad active category : 'IN' or 'OUT'
  - jumlah (bigint) -- Total aggregate headcount of staff in this slice (Use SUM(jumlah) to calculate total staff/dosen headcount)
  - dim_waktu_snapshot_id (integer) -- Snapshot date key
  - tanggal_snapshot (date) -- Snapshot compile date
  - created_at (timestamp with time zone) -- Timestamp of record insertion
  - jenis_pegawai (text) -- Staff type filter: 'Dosen' (Teachers/Faculty members/Lecturers/Civitas Akademika), 'Tendik' (Support staff/Administrators/Librarians/Operators)
  - status_pegawai (text) -- Employment status: 'PNS' (Civil Servant), 'Non-PNS' (Permanent Contract), 'Kontrak' (Temporary), 'Honorer' (Casual worker)
  - pendidikan_tertinggi (text) -- Completed degree level: 'Sarjana', 'Magister', 'Diploma Satu', 'Sekolah Menengah Akhir', 'Sekolah Dasar'
Semantic Keywords & Translation Encodings: jumlah dosen, total pegawai, jumlah guru, trend pegawai, PNS Kontrak, perkembangan staff tahunan, aggregate headcount statistics, Dosen, Tendik, active lecturers count, historical employee growth trends, S1, S2, S3"""


    # --- 3. PUBLIC SCHEMA (1 TABLE) ---
    dim_waktu_def = """Database Table Definition Asset:
Table: public.dim_waktu
Description: Core calendar and dimensional time table used to map dates to days, months, quarters, and years in the data warehouse.
Columns:
  - tanggal (date) -- Date key representing year, month, and day
  - id_waktu (character varying) -- String date code
  - bulan (integer) -- Numeric month code (1 = Januari, 2 = Februari, ..., 12 = Desember)
  - tahun (integer) -- Numeric year code (e.g., 2024, 2025)
  - quarter (integer) -- Calendar quarter: 1, 2, 3, 4
  - periode (character varying) -- Formatted year-month code (e.g., '2024-07')
  - hari (integer) -- Day of month: 1 to 31
  - nama_hari (character varying) -- Indonesian name of day ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
  - minggu_ke (integer) -- Ordinal week number of the year: 1 to 53
  - id (bigint) -- Internal sequence key
Semantic Keywords & Translation Encodings: tanggal, bulan, tahun, kuartal, nama hari, akhir pekan, kalender harian, waktu berjalan, calendar year lookup, time dimensions, bulan, tahun"""


    # Collect all definitions into structured lists for batch upsert execution
    ids = [
        # Academic Tables
        "schema_akademik_dim_periode_definition",
        "schema_akademik_dim_mahasiswa_definition",
        "schema_akademik_dim_status_keaktifan_mahasiswa_definition",
        "schema_akademik_fact_penyematan_status_mahasiswa_definition",
        "schema_akademik_dim_jenis_keluar_mahasiswa_definition",
        "schema_akademik_statis_aggr_penyematan_status_mahasiswa_definition",
        "schema_akademik_statis_penyematan_status_mahasiswa_definition",
        "schema_akademik_statis_aggr_lintas_periode_penyematan_status_mahasiswa_definition",
        "schema_akademik_dim_bidang_studi_definition",
        "schema_akademik_statis_bidang_studi_definition",
        "schema_akademik_rep_perbandingan_jumlah_mahasiswa_lintas_periode_definition",
        # Kepegawaian Tables
        "schema_kepegawaian_dim_pegawai_definition",
        "schema_kepegawaian_dim_satuan_kerja_definition",
        "schema_kepegawaian_dim_jenis_keluar_pegawai_definition",
        "schema_kepegawaian_fact_riwayat_status_pegawai_definition",
        "schema_kepegawaian_dim_status_keaktifan_pegawai_definition",
        "schema_kepegawaian_statis_riwayat_status_pegawai_definition",
        "schema_kepegawaian_statis_aggr_riwayat_status_pegawai_definition",
        # Public Time Table
        "schema_public_dim_waktu_definition"
    ]

    documents = [
        # Academic
        dim_periode_def,
        dim_mahasiswa_def,
        dim_status_keaktifan_mahasiswa_def,
        fact_penyematan_status_mahasiswa_def,
        dim_jenis_keluar_mahasiswa_def,
        statis_aggr_penyematan_status_mahasiswa_def,
        statis_penyematan_status_mahasiswa_def,
        statis_aggr_lintas_periode_penyematan_status_mahasiswa_def,
        dim_bidang_studi_def,
        statis_bidang_studi_def,
        rep_perbandingan_jumlah_mahasiswa_lintas_periode_def,
        # Kepegawaian
        dim_pegawai_def,
        dim_satuan_kerja_def,
        dim_jenis_keluar_pegawai_def,
        fact_riwayat_status_pegawai_def,
        dim_status_keaktifan_pegawai_def,
        statis_riwayat_status_pegawai_def,
        statis_aggr_riwayat_status_pegawai_def,
        # Public
        dim_waktu_def
    ]

    metadatas = [{"type": "schema_ddl"} for _ in range(len(ids))]

    print("[TRAINING] Upserting 19 annotated schemas directly to ChromaDB...")
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print("\n" + "═"*60)
    print(" 🎉 [SUCCESS] CHROMADB METADATA TRAINED SUCCESSFULLY!")
    print("   Total tables configured: 19")
    print("   Target DB collection  : vanna_collection")
    print("   Accuracy upgrade      : Data Domain Domain & English-Indonesian term bindings active.")
    print("═"*60)

except Exception as e:
    print(f"\n🚨 [CRITICAL RUNTIME ERROR]: Failed to train data dictionary: {e}")