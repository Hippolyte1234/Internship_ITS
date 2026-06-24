import chromadb

# Pass the path to the DIRECTORY containing your chroma.sqlite3 file (do not include the filename)
client = chromadb.PersistentClient(path="./vanna_knowledge_base/")

# Get a list of all existing collections
collections = client.list_collections()

if not collections:
    print("No collections found in this database.")
else:
    # 1. Print all available names so you can see them
    print("Available collections:")
    for col in collections:
        print(f" - {col.name}")
    
    # 2. Automatically grab the first collection name dynamically
    first_collection_name = collections[0].name
    print(f"\nAutomatically reading from: '{first_collection_name}'")
    
    # 3. Fetch the data using that name
    collection = client.get_collection(name=first_collection_name)
    results = collection.get(include=["documents", "metadatas"])
    
    print("\nSample Data:")
    print(results)
