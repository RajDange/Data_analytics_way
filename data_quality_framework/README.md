# Data Quality Framework – Microsoft Fabric

A metadata-driven data quality runner for the EBS customer master, built in the Fabric Lakehouse `Customer_MDM_PoC`.
DQ rules are stored in a catalog table and run by one generic notebook. The results feed a Power BI data quality dashboard.

## Notebooks (`notebooks/`)

| Notebook | Purpose | When to run |
|---|---|---|
| `00_dq_config` | Shared settings: lakehouse, schemas, table names, timezone, retention | Never on its own – loaded by the others via `%run` |
| `01_dq_setup` | Creates the `dq` schema and all DQ tables, seeds DQ dimensions, builds `dim_date` | Once (safe to re-run) |
| `02_dq_rule_onboarding` | Defines rules and MERGEs them into `dq_rule_catalog` (versioned) | Whenever rules are added or changed |
| `03_dq_runner` | Runs all active rules, writes the run log and failed records | Scheduled, after the EBS load |

## Tables (`Customer_MDM_PoC.dq`)

| Table | Load | Content |
|---|---|---|
| `dq_dimension` | static | DQ dimensions (Completeness, Validity, Uniqueness, …) |
| `dq_rule_catalog` | merge | Rules: `base_sql` (population), `failure_condition` / `failure_sql`, metadata, version |
| `dq_run` | append | One row per runner execution and its status |
| `dq_rule_run_log` | append | One row per rule per run: total, failed, passed, pass rate, status |
| `dq_failed_records_history` | append (partitioned by `run_date`) | Failing keys of every run |
| `dq_failed_records_current` | overwrite | Failing keys of the latest run, with `first_failed_date` and `days_failing` |
| `dim_date` | static | Date dimension 2024–2030 |

## Rule contract

- `base_sql` is the population, and its count is the denominator. It must return `record_key` plus every column used by the condition.
- `failure_condition` is a filter applied to `base_sql`, for simple rules.
- `failure_sql` is a full query that returns the failing `record_key`s. It is used for complex rules (duplicates, cross-table checks) when `failure_condition` is NULL.
- All SQL is Spark SQL. Source tables are referenced as `{SRC}.table_name`.

## Setup

1. Import the four notebooks into the workspace, keeping their names, and attach `Customer_MDM_PoC` as the default lakehouse.
2. Adjust `SRC_SCHEMA` in `00_dq_config` if needed.
3. Run `01_dq_setup` once.
4. Add rules in `02_dq_rule_onboarding`, run its test cell, then its MERGE cell.
5. Run `03_dq_runner` manually to check the results, then schedule it in a Data Pipeline after the EBS load.
