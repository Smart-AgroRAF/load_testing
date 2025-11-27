import pandas as pd

class Stats:
    """
    Aggregates statistics over one or more CSV result files.
    Categories are NOT used — each CSV is already separated externally.
    """

    def __init__(self, percentiles=None):
        self.df = pd.DataFrame()
        self.percentiles = sorted([p for p in (percentiles or []) if 0 < p < 1])

    # def load_multiple_csv(self, *paths):
    #     """
    #     Load multiple CSVs and merge them into a single dataframe.
    #     Example:
    #         stats.load_multiple_csv("tx_build.csv", "read_only.csv")
    #     """
    #     frames = []

    #     for path in paths:
    #         df = pd.read_csv(path)

    #         df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
    #         df.dropna(subset=["duration"], inplace=True)

    #         frames.append(df)

    #     self.df = pd.concat(frames, ignore_index=True)

    def load_multiple_csv(self, files):
        frames = []

        for path, _label in files:
            df = pd.read_csv(path)
            df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
            df.dropna(subset=["duration"], inplace=True)
            frames.append(df)

        self.df = pd.concat(frames, ignore_index=True)

    # ---- Helpers ----
    def _compute_stats(self, group: pd.DataFrame):
        stats = {
            "count": len(group),
            "mean": group["duration"].mean(),
            "median": group["duration"].median(),
            "std": group["duration"].std(),
            "min": group["duration"].min(),
            "max": group["duration"].max(),
        }

        for p in self.percentiles:
            stats[f"p{int(p * 100)}"] = group["duration"].quantile(p)

        return pd.Series(stats)

    # ---- Stats by dimensions ----
    def stats_by_task(self):
        return (
            self.df.groupby("task")[["duration"]]
            .apply(lambda g: self._compute_stats(g))
            .reset_index()
        )

    def stats_by_endpoint(self):
        return (
            self.df.groupby("endpoint")[["duration"]]
            .apply(lambda g: self._compute_stats(g))
            .reset_index()
        )

    def stats_by_task_and_endpoint(self):
        return (
            self.df.groupby(["task", "endpoint"])[["duration"]]
            .apply(lambda g: self._compute_stats(g))
            .reset_index()
        )

    # ---- Global stats ----
    def global_stats(self, total_time: float, phase):
        df = self.df

        # total_requests = len(df)
        if phase == "api-tx-build":
            success_api = ((df["status"] == "success") & (df["task"] == "API-TX-BUILD")).sum()
            success_blockchain = ((df["status"] == "success") & (df["task"] == "TX-BLOCK")).sum()
            
            fails_api = ((df["status"] == "fail") & (df["task"] == "API-TX-BUILD")).sum()
            fails_blockchain = ((df["status"] == "fail") & (df["task"] == "TX-BLOCK")).sum()

            total_requests_api = (df["task"] == "API-TX-BUILD").sum()
            total_requests_blockchain = (df["task"] == "TX-BLOCK").sum()
            rps_api = total_requests_api / total_time if total_time > 0 else 0
            rps_blockchain = total_requests_blockchain / total_time if total_time > 0 else 0
            
            return pd.DataFrame([{
                "total_requests_api": total_requests_api,
                "total_requests_blockchain": total_requests_blockchain,
                "success_api": success_api,
                "success_blockchain": success_blockchain,
                "fails_api": fails_api,
                "fails_blockchain": fails_blockchain,
                "rps_api": rps_api,
                "rps_blockchain": rps_blockchain,
                "total_time": total_time,
            }])

        elif phase == "api-read-only":
            success = (df["status"] == "success").sum()
            fails = (df["status"] == "fail").sum()

            total_requests_api = (df["task"] == "API-READ-ONLY").sum()
            rps_api = total_requests_api / total_time if total_time > 0 else 0
        
            return pd.DataFrame([{
                "total_requests_api": total_requests_api,
                "success": success,
                "fails": fails,
                "rps_api": rps_api,
                "total_time": total_time,
            }])

    # ---- Save ----
    def save_stats_by_task(self, path):
        self.stats_by_task().to_csv(path, index=False)

    def save_stats_by_endpoint(self, path):
        self.stats_by_endpoint().to_csv(path, index=False)

    def save_stats_by_task_and_endpoint(self, path):
        self.stats_by_task_and_endpoint().to_csv(path, index=False)

    def save_global_stats(self, path, total_time, phase):
        self.global_stats(total_time, phase).to_csv(path, index=False)
