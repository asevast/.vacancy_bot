import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


def cluster_vacancies(df):
    """ML clustering by complexity"""
    if len(df) < 5:
        return df.assign(cluster="mixed")
    
    if 'salary' not in df.columns or df['salary'].isna().all():
        return df.assign(cluster="unknown")
    
    df = df.copy()
    df['description'] = df['description'].fillna('')
    df['skills'] = df['skills'].apply(lambda x: ' '.join(x) if isinstance(x, list) else str(x))
    
    text_data = df['description'] + ' ' + df['skills'].astype(str)
    vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    X = vectorizer.fit_transform(text_data)
    
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    df_temp = df.copy()
    df_temp['cluster_num'] = clusters
    cluster_salaries = df_temp.groupby('cluster_num')['salary'].mean().sort_values()
    cluster_ids = list(cluster_salaries.index)
    
    if len(cluster_ids) < 3:
        salary_series = df['salary'].fillna(0)
        if salary_series.nunique() >= 3:
            try:
                ranks = salary_series.rank(method="first")
                labels = pd.qcut(ranks, 3, labels=["Junior", "Middle", "Senior"])
                return df.assign(cluster=labels.astype(str))
            except Exception:
                pass
        ordered_labels = ["Junior", "Middle", "Senior"]
        mapping = {cid: ordered_labels[i] for i, cid in enumerate(cluster_ids)}
        return df.assign(cluster=[mapping.get(c, "mixed") for c in clusters])

    mapping = {
        cluster_ids[0]: "Junior",
        cluster_ids[1]: "Middle",
        cluster_ids[2]: "Senior"
    }
    
    return df.assign(cluster=[mapping.get(c, "Middle") for c in clusters])
