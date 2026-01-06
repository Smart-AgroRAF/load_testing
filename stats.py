import csv
import os
import pandas as pd

class Stats:
    """
    Aggregates statistics over one or more CSV result files.
    Categories are NOT used — each CSV is already separated externally.
    """

    def __init__(self, percentiles=None):
        self.df = pd.DataFrame()
        self.percentiles = sorted([p for p in (percentiles or []) if 0 < p < 1])

    def load_multiple_csv(self, files):
        frames = []

        for path, _label in files:
            df = pd.read_csv(path)
            
            # Ensure duration and timestamp are numeric
            df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
            
            df.dropna(subset=["duration"], inplace=True)
            frames.append(df)

        self.df = pd.concat(frames, ignore_index=True)

    # ---- Helpers ----
    def _compute_stats(self, group: pd.DataFrame):
        count = len(group)
        if count == 0:
            return pd.Series(dtype=float)
        
        stats = {
            "count": count,
            "mean": group["duration"].mean(),
            "median": group["duration"].median(),
            "std": group["duration"].std(),
            "min": group["duration"].min(),
            "max": group["duration"].max(),
        }
        
        # Add success/fail counts if status column exists
        if "status" in group.columns:
            stats["success_count"] = (group["status"] == "success").sum()
            stats["fail_count"] = (group["status"] == "fail").sum()

        for p in self.percentiles:
            stats[f"p{int(p * 100)}"] = group["duration"].quantile(p)

        return pd.Series(stats)

    # ---- Stats by dimensions ----
    def stats_by_task(self):
        return (
            self.df.groupby("task")[["duration", "status"]]
            .apply(lambda g: self._compute_stats(g))
            .reset_index()
        )

    def stats_by_endpoint(self):
        # Filter for representative tasks to avoid overcounting operations
        # 'FULL' represents a write operation (API + BC)
        # 'API-READ-ONLY' represents a read operation
        representative_tasks = ["FULL", "API-READ-ONLY"]
        df_rep = self.df[self.df["task"].isin(representative_tasks)]
        
        # Fallback if no representative tasks found (e.g. old data or different phase)
        if df_rep.empty:
            df_rep = self.df

        return (
            df_rep.groupby("endpoint")[["duration", "status"]]
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
    def global_stats(self, phase, total_time: float = None):
        df = self.df

        # If total_time is not provided, calculate it from timestamps
        if total_time is None:
            if not df.empty and "timestamp" in df.columns:
                start_ts = df["timestamp"].min()
                end_ts = df["timestamp"].max()
                total_time = end_ts - start_ts
            
            # Default to a small value if 0 or still None to avoid division by zero
            if total_time is None or total_time <= 0:
                total_time = 1.0 

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


