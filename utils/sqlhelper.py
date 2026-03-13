

SQL = {
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

