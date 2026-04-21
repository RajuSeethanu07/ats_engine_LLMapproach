import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class VectorStore:

    def __init__(self):
        self.skills = []
        self.vectors = []

    def add(self, skill: str, vector: list):
        self.skills.append(skill)
        self.vectors.append(vector)

    def search(self, query_vector: list, top_k=1):
        if not self.vectors:
            return []

        sims = cosine_similarity([query_vector], self.vectors)[0]

        top_indices = np.argsort(sims)[::-1][:top_k]

        return [
            {
                "skill": self.skills[i],
                "score": float(sims[i])
            }
            for i in top_indices
        ]