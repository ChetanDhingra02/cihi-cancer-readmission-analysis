

import duckdb


# Create/open our local database
con = duckdb.connect("output/dad.duckdb")


# ------------------------------------------------------------
# Create the admissions table
# ------------------------------------------------------------

con.execute("DROP TABLE IF EXISTS admissions")

con.execute("""
    CREATE TABLE admissions AS

    SELECT
        ROW_NUMBER() OVER () AS record_id,
        *

    FROM 'output/dad_parsed.parquet'
""")


n_admissions = con.execute(
    "SELECT COUNT(*) FROM admissions"
).fetchone()[0]

print(
    f"admissions table: "
    f"{n_admissions:,} rows"
)


# ------------------------------------------------------------
# Run our reshape SQL
# ------------------------------------------------------------

with open("sql/01_reshape.sql") as file:

    sql = file.read()

    con.execute(sql)


# Count the resulting rows
n_dx = con.execute(
    "SELECT COUNT(*) FROM diagnoses"
).fetchone()[0]

n_px = con.execute(
    "SELECT COUNT(*) FROM interventions"
).fetchone()[0]


print(
    f"diagnoses table:  "
    f"{n_dx:,} rows"
)

print(
    f"interventions:    "
    f"{n_px:,} rows"
)


# ------------------------------------------------------------
# Some basic checks
# ------------------------------------------------------------

print("\nDiagnoses per admission:")

print(
    con.execute("""
        SELECT
            ROUND(AVG(n), 2) AS mean_diagnoses,
            MEDIAN(n) AS median_diagnoses,
            MAX(n) AS max_diagnoses

        FROM (
            SELECT
                record_id,
                COUNT(*) AS n

            FROM diagnoses

            GROUP BY record_id
        )
    """).df()
)


print("\nDiagnosis type breakdown:")

print(
    con.execute("""
        SELECT
            dx_type,

            CASE dx_type

                WHEN 'M'
                    THEN 'Most responsible for the stay'

                WHEN '1'
                    THEN 'Already present on admission'

                WHEN '2'
                    THEN 'Developed during the stay'

                WHEN 'W'
                    THEN 'Service transfer'

                WHEN 'X'
                    THEN 'Service transfer'

                ELSE 'Other'

            END AS meaning,

            COUNT(*) AS n

        FROM diagnoses

        GROUP BY dx_type

        ORDER BY n DESC
    """).df()
)


con.close()

print(
    "\nDatabase saved to "
    "output/dad.duckdb"
)