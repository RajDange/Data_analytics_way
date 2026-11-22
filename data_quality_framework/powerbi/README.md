# DQ Dashboard – Power BI project (PBIP / PBIR)

A Power BI report generated from the design mockup: 4 pages at 1280×720, live-connected to the semantic model `SM_DQ_Customer`.
The report contains no data. It reads everything from the model.

| Page | Visuals |
|---|---|
| Overview | 5 slicers, 5 KPI cards, score by dimension (bar), score trend (line), failing rules table, SharePoint link |
| DQ Trend | 5 slicers, score by day (record-weighted vs rule-average), rules executed by day, score by dimension by day |
| Rule Audit | 5 slicers (no OU slicers, on purpose), 2 cards, rule run log table |
| Failed Records | 5 slicers (account no., site ID, dimension, rule, OU), 2 cards, SharePoint link, records-to-fix table |

Slicers that use the same field are synced across pages: a dimension or OU picked on one page applies on the others.

## 1. Point the report at your semantic model
Edit `DQ_Dashboard.Report/definition.pbir` and replace:
- `[WorkspaceName]`: the Fabric workspace name, exactly as shown in Fabric.
- `[SemanticModelId]`: the model's ID, the GUID in the browser URL when the semantic model is open (`.../datasets/<id>/...`).
- `SM_DQ_Customer`: change it if your model has a different name.

## 2. Open it in Power BI Desktop
1. Clone or download this repo folder.
2. In Power BI Desktop, check *File → Options → Preview features*. If you see *Power BI Project (.pbip) save option* and *Store reports using enhanced metadata format (PBIR)*, turn them on. Recent versions may have them on by default.
3. Open `DQ_Dashboard.pbip`.

## 3. Names the report expects in the model
A visual showing a **"Fix this"** or **"Something's wrong with one or more fields"** message means one of these names doesn't match your model exactly. Rename it in the visual's field well, or tell Claude the real name so the generator can be updated.

**Tables and columns**
- `dim_date[date]`
- `dq_dimension[dimension_name]`
- `dq_rule_catalog[rule_name]`, `[dimension_name]`, `[severity]`, `[rule_description]`
- `dim_operating_unit[ou_name]`, `[region]`
- `dq_rule_run_log[run_date]`, `[rule_id]`, `[rule_version]`, `[status]`, `[total_count]`, `[failed_count]`, `[pass_rate]`, `[duration_sec]`, `[error_message]`
- `dq_failed_records_current[record_key]`, `[account_number]`, `[party_number]`, `[cust_acct_site_id]`, `[first_failed_date]`, `[days_failing]`

**Measures** (on table `dq_rule_run_log`)
- `DQ Score %`
- `DQ Score % (Rule Avg)`
- `DQ Score % (Latest)`
- `DQ Score Change (pp)`
- `Failed Records (Latest)`
- `Failing Records (Current)`
- `Records Failing > 30 Days`
- `Rules Executed`
- `Rules Errored`
- `Rules Errored (Latest)`

If your measures sit on a different table, change `MEASURE_TABLE` in `tools/gen_pbir.py` and regenerate.

## 4. Finish in Desktop (not generated)
- **SharePoint link:** the URL in the two link text boxes is a placeholder. Replace it with your folder link.
- **Drill-through:** Failed Records page → Page information → Drill-through, fields `rule_name` and `dimension_name`.
- **Status highlight:** add conditional formatting on `status` in the Rule Audit table.
- **Top N:** optionally add a Top 5 filter on the Overview table.
- **Navigation:** optionally add page navigation buttons.
- **Formatting:** set number formats on the measures in the model, e.g. percentages with 1 decimal place.

Save in Desktop as `.pbip`, then commit. Desktop rewrites the files in its own canonical form.

## Regenerating
`tools/gen_pbir.py` generates the report folder. It was validated against Microsoft's published PBIR JSON schemas
(`report 1.0.0`, `page 1.0.0`, `visualContainer 1.0.0`). Schema validation checks the file structure only. It can't
check that table, column and measure names exist in your model, or that Desktop accepts every visual role and formatting
property, so the first open in Desktop is the real test.
