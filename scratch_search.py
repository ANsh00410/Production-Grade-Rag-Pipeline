# from app.retrieval.search import sparse_search

# query = "how do I deploy to production"
# results = sparse_search(query, top_k=10)

# print(f"SPARSE-ONLY results for: {query!r}\n")
# for i, r in enumerate(results, 1):
#     print(f"{i}. score={r.score:.4f}  [{r.payload['heading_path']}]")
#     print(f"   {r.payload['text'][:100]}...\n")

from app.retrieval.retrieve import retrieve
results = retrieve('how do I deploy to production', final_k=5)
for r in results:
    print(f"{r.score:.4f}  [{r.payload['heading_path']}]")
    print(f"   {r.payload['text'][:100]}...\n")