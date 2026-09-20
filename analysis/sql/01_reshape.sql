-- Convert the wide diagnosis and intervention columns
-- into long tables.

-- ============================================================
-- DIAGNOSES
-- ============================================================

CREATE OR REPLACE TABLE diagnoses AS

SELECT
    record_id,
    CAST(dx_seq AS INTEGER) AS dx_seq,
    dx_code,
    dx_type

FROM (

    UNPIVOT (
        SELECT
            record_id,

            D_I10_1,  D_TYP_1,
            D_I10_2,  D_TYP_2,
            D_I10_3,  D_TYP_3,
            D_I10_4,  D_TYP_4,
            D_I10_5,  D_TYP_5,
            D_I10_6,  D_TYP_6,
            D_I10_7,  D_TYP_7,
            D_I10_8,  D_TYP_8,
            D_I10_9,  D_TYP_9,
            D_I10_10, D_TYP_10,
            D_I10_11, D_TYP_11,
            D_I10_12, D_TYP_12,
            D_I10_13, D_TYP_13,
            D_I10_14, D_TYP_14,
            D_I10_15, D_TYP_15,
            D_I10_16, D_TYP_16,
            D_I10_17, D_TYP_17,
            D_I10_18, D_TYP_18,
            D_I10_19, D_TYP_19,
            D_I10_20, D_TYP_20,
            D_I10_21, D_TYP_21,
            D_I10_22, D_TYP_22,
            D_I10_23, D_TYP_23,
            D_I10_24, D_TYP_24,
            D_I10_25, D_TYP_25

        FROM admissions
    )

    ON
       (D_I10_1,  D_TYP_1)  AS "1",
       (D_I10_2,  D_TYP_2)  AS "2",
       (D_I10_3,  D_TYP_3)  AS "3",
       (D_I10_4,  D_TYP_4)  AS "4",
       (D_I10_5,  D_TYP_5)  AS "5",
       (D_I10_6,  D_TYP_6)  AS "6",
       (D_I10_7,  D_TYP_7)  AS "7",
       (D_I10_8,  D_TYP_8)  AS "8",
       (D_I10_9,  D_TYP_9)  AS "9",
       (D_I10_10, D_TYP_10) AS "10",
       (D_I10_11, D_TYP_11) AS "11",
       (D_I10_12, D_TYP_12) AS "12",
       (D_I10_13, D_TYP_13) AS "13",
       (D_I10_14, D_TYP_14) AS "14",
       (D_I10_15, D_TYP_15) AS "15",
       (D_I10_16, D_TYP_16) AS "16",
       (D_I10_17, D_TYP_17) AS "17",
       (D_I10_18, D_TYP_18) AS "18",
       (D_I10_19, D_TYP_19) AS "19",
       (D_I10_20, D_TYP_20) AS "20",
       (D_I10_21, D_TYP_21) AS "21",
       (D_I10_22, D_TYP_22) AS "22",
       (D_I10_23, D_TYP_23) AS "23",
       (D_I10_24, D_TYP_24) AS "24",
       (D_I10_25, D_TYP_25) AS "25"

    INTO NAME dx_seq VALUE dx_code, dx_type
)

WHERE dx_code IS NOT NULL
  AND dx_code <> '';


-- ============================================================
-- INTERVENTIONS
-- ============================================================

CREATE OR REPLACE TABLE interventions AS

SELECT
    record_id,
    CAST(px_seq AS INTEGER) AS px_seq,
    px_code,
    anaesthetic

FROM (

    UNPIVOT (
        SELECT
            record_id,

            I_CCI_1,  AN_TE_1,
            I_CCI_2,  AN_TE_2,
            I_CCI_3,  AN_TE_3,
            I_CCI_4,  AN_TE_4,
            I_CCI_5,  AN_TE_5,
            I_CCI_6,  AN_TE_6,
            I_CCI_7,  AN_TE_7,
            I_CCI_8,  AN_TE_8,
            I_CCI_9,  AN_TE_9,
            I_CCI_10, AN_TE_10,
            I_CCI_11, AN_TE_11,
            I_CCI_12, AN_TE_12,
            I_CCI_13, AN_TE_13,
            I_CCI_14, AN_TE_14,
            I_CCI_15, AN_TE_15,
            I_CCI_16, AN_TE_16,
            I_CCI_17, AN_TE_17,
            I_CCI_18, AN_TE_18,
            I_CCI_19, AN_TE_19,
            I_CCI_20, AN_TE_20

        FROM admissions
    )

    ON
       (I_CCI_1,  AN_TE_1)  AS "1",
       (I_CCI_2,  AN_TE_2)  AS "2",
       (I_CCI_3,  AN_TE_3)  AS "3",
       (I_CCI_4,  AN_TE_4)  AS "4",
       (I_CCI_5,  AN_TE_5)  AS "5",
       (I_CCI_6,  AN_TE_6)  AS "6",
       (I_CCI_7,  AN_TE_7)  AS "7",
       (I_CCI_8,  AN_TE_8)  AS "8",
       (I_CCI_9,  AN_TE_9)  AS "9",
       (I_CCI_10, AN_TE_10) AS "10",
       (I_CCI_11, AN_TE_11) AS "11",
       (I_CCI_12, AN_TE_12) AS "12",
       (I_CCI_13, AN_TE_13) AS "13",
       (I_CCI_14, AN_TE_14) AS "14",
       (I_CCI_15, AN_TE_15) AS "15",
       (I_CCI_16, AN_TE_16) AS "16",
       (I_CCI_17, AN_TE_17) AS "17",
       (I_CCI_18, AN_TE_18) AS "18",
       (I_CCI_19, AN_TE_19) AS "19",
       (I_CCI_20, AN_TE_20) AS "20"

    INTO NAME px_seq VALUE px_code, anaesthetic
)

WHERE px_code IS NOT NULL
  AND px_code <> '';