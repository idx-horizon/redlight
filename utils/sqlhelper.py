

SQL = {

    "atoz": """
WITH distinct_events AS (
    SELECT DISTINCT 
        runner_id,
        TRIM(event) AS event,
        SUBSTR(TRIM(event), 1, 1) AS initial
    FROM runs
    WHERE event IS NOT NULL
),
run_counts AS (
    SELECT 
        runner_id,
        SUBSTR(TRIM(event), 1, 1) AS initial,
        COUNT(*) AS total_runs
    FROM runs
    WHERE event IS NOT NULL
    GROUP BY runner_id, initial
)
SELECT 
    d.initial,
    COUNT(*) AS event_count,
    r.total_runs,
    GROUP_CONCAT(d.event, ', ') AS events
FROM distinct_events d
JOIN run_counts r
  ON d.runner_id = r.runner_id
 AND d.initial = r.initial
WHERE d.runner_id = ?
GROUP BY d.initial, r.total_runs
ORDER BY d.initial;
    """,

    "pbs": """
    WITH ranked AS (
        SELECT runner_id,
               known_as,
               time AS original_time,
               CASE
                   WHEN LENGTH(time) <= 5 THEN '0:' || time  -- normalize MM:SS to 0:MM:SS
                   ELSE time
               END AS sort_time,
               ROW_NUMBER() OVER (
                   PARTITION BY runner_id
                   ORDER BY
                       CASE
                           WHEN LENGTH(time) <= 5 THEN '0:' || time
                           ELSE time
                       END ASC
               ) AS rn
        FROM vw_runner_runs
        where known_as = ? COLLATE NOCASE
    )
    SELECT runner_id,
        known_as,
        original_time AS min_time
    FROM ranked
    WHERE rn = 1
    ORDER BY runner_id;
    """,

    "stats_pb_compare": """
      SELECT
        COUNT(*) AS total_events,
        SUM(CASE WHEN r1_pb < r2_pb THEN 1 ELSE 0 END) AS r1_wins,
        SUM(CASE WHEN r2_pb < r1_pb THEN 1 ELSE 0 END) AS r2_wins,
        SUM(CASE WHEN r1_pb = r2_pb THEN 1 ELSE 0 END) AS ties
      FROM (
         SELECT
            r1.event,
            MIN(r1.time) AS r1_pb,
            MIN(r2.time) AS r2_pb
         FROM runs r1
         JOIN runs r2 ON r1.event = r2.event
         WHERE r1.runner_id = ?
           AND r2.runner_id = ?
         GROUP BY r1.event
      )
    """,

   "total_event_pb_count": """
     SELECT COUNT(*) FROM (
         SELECT r1.event
         FROM runs r1
         JOIN runs r2 ON r1.event = r2.event
         WHERE r1.runner_id = ? AND r2.runner_id = ?
         GROUP BY r1.event
     )""",

  "compare_pb": """
    SELECT r.event, r1_time, r2_time
    FROM (
        SELECT r1.event
        FROM runs r1
        JOIN runs r2 ON r1.event = r2.event
        WHERE r1.runner_id = ? AND r2.runner_id = ?
        GROUP BY r1.event
        ORDER BY r1.event
        LIMIT ? OFFSET ?
    ) AS r
   JOIN (
        SELECT r1.event, MIN(r1.time) AS r1_time
        FROM runs r1
        WHERE r1.runner_id = ?
        GROUP BY r1.event
    ) AS r1_pb_table ON r1_pb_table.event = r.event
    JOIN (
        SELECT r2.event, MIN(r2.time) AS r2_time
        FROM runs r2
        WHERE r2.runner_id = ?
        GROUP BY r2.event
    ) AS r2_pb_table ON r2_pb_table.event = r.event
    ORDER BY r.event;
  """

}
def get_sql(snippet):
    return SQL[snippet]

