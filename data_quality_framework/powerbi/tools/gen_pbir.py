"""Generate a Power BI project (PBIP, PBIR format) for the DQ dashboard.

Pages / layout follow the design mockup (1280x720). Visuals bind to the semantic model SM_DQ_Customer
(tables from Customer_MDM_PoC.dq, measures hosted on dq_rule_run_log).
"""
import json, os, shutil, hashlib, uuid

ROOT        = "/home/claude/data_analytics_way/data_quality_framework/powerbi"
REPORT_NAME = "DQ_Dashboard"
REPORT_DIR  = f"{ROOT}/{REPORT_NAME}.Report"
DEF         = f"{REPORT_DIR}/definition"

S = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
SCHEMA = {
    "version": f"{S}/versionMetadata/1.0.0/schema.json",
    "report":  f"{S}/report/1.0.0/schema.json",
    "pages":   f"{S}/pagesMetadata/1.0.0/schema.json",
    "page":    f"{S}/page/1.0.0/schema.json",
    "visual":  f"{S}/visualContainer/1.0.0/schema.json",
}

MEASURE_TABLE = "dq_rule_run_log"   # table the measures were created on

# ------------------------------------------------------------------ helpers
def hid(*parts, n=20):
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:n]

def lit(v):                       # literal expression
    return {"expr": {"Literal": {"Value": v}}}

def s(text):  return lit("'" + text.replace("'", "''") + "'")
def num(n):   return lit(f"{n}D")
def b(flag):  return lit("true" if flag else "false")
def color(hexc): return {"solid": {"color": s(hexc)}}

def col(table, column):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}},
            "queryRef": f"{table}.{column}", "nativeQueryRef": column}

def meas(name, table=MEASURE_TABLE):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
            "queryRef": f"{table}.{name}", "nativeQueryRef": name}

def container_objects(title=None, bg=True):
    o = {}
    if title is not None:
        o["title"] = [{"properties": {"show": b(True), "text": s(title), "fontSize": num(11),
                                      "bold": b(True), "fontColor": color("#1B2430")}}]
    if bg:
        o["background"] = [{"properties": {"show": b(True), "color": color("#FFFFFF"), "transparency": num(0)}}]
        o["border"] = [{"properties": {"show": b(True), "color": color("#E1E5EB"), "radius": num(8)}}]
    return o

def visual(page, key, x, y, w, h, vtype, roles=None, title=None, sort=None, objects=None,
           sync=None, bg=True, z=0):
    v = {"visualType": vtype}
    if roles:
        q = {"queryState": {r: {"projections": p} for r, p in roles.items()}}
        if sort:
            field, direction = sort
            q["sortDefinition"] = {"sort": [{"field": field["field"], "direction": direction}],
                                   "isDefaultSort": False}
        v["query"] = q
    if objects:
        v["objects"] = objects
    vco = container_objects(title, bg)
    if vco:
        v["visualContainerObjects"] = vco
    if sync:
        v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    name = hid(page, key)
    return name, {"$schema": SCHEMA["visual"], "name": name,
                  "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
                  "visual": v}

def textbox(page, key, x, y, w, h, runs, fill=None, z=0):
    paragraphs = [{"textRuns": runs}]
    v = {"visualType": "textbox",
         "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]}}
    vco = {}
    if fill:
        vco["background"] = [{"properties": {"show": b(True), "color": color(fill), "transparency": num(0)}}]
    else:
        vco["background"] = [{"properties": {"show": b(False)}}]
    v["visualContainerObjects"] = vco
    name = hid(page, key)
    return name, {"$schema": SCHEMA["visual"], "name": name,
                  "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
                  "visual": v}

def run(text, size="11pt", bold=False, colr="#1B2430", url=None):
    r = {"value": text, "textStyle": {"fontSize": size, "color": colr}}
    if bold:
        r["textStyle"]["fontWeight"] = "bold"
    if url:
        r["url"] = url
    return r

SLICER_OBJ = {"data": [{"properties": {"mode": s("Dropdown")}}],
              "header": [{"properties": {"show": b(True), "fontColor": color("#4B5563"), "textSize": num(9)}}]}

def header(page, title_suffix):
    return [textbox(page, "hdr", 0, 0, 1280, 52,
                    [run("Customer Master – Data Quality", "16pt", True, "#FFFFFF"),
                     run("   |   " + title_suffix, "12pt", False, "#DCE5F0")],
                    fill="#1F3A5F", z=0)]

def slicer_row(page, fields):
    out, x, w = [], 20, 236
    for i, (key, field, sync) in enumerate(fields):
        out.append(visual(page, f"sl_{key}", x + i * (w + 12), 60, w, 56, "slicer",
                          roles={"Values": [field]}, objects=SLICER_OBJ, sync=sync, bg=True, z=100 + i))
    return out

def card(page, key, x, y, w, h, m, z):
    return visual(page, key, x, y, w, h, "card", roles={"Values": [meas(m)]},
                  objects={"labels": [{"properties": {"fontSize": num(22), "color": color("#1B2430")}}],
                           "categoryLabels": [{"properties": {"show": b(True), "fontSize": num(10),
                                                              "color": color("#4B5563")}}]}, z=z)

SP_URL = "https://YOUR-TENANT.sharepoint.com/sites/YOUR-SITE/Shared%20Documents/DQ%20Exports"

# common slicer fields
F_DATE   = col("dim_date", "date")
F_DIM    = col("dq_dimension", "dimension_name")
F_REGION = col("dim_operating_unit", "region")
F_OU     = col("dim_operating_unit", "ou_name")
F_RULE   = col("dq_rule_catalog", "rule_name")
F_SEV    = col("dq_rule_catalog", "severity")

# ------------------------------------------------------------------ pages
pages = []

# 1. Overview
p = "Overview"
v = header(p, "Overview")
v += slicer_row(p, [("date", F_DATE, "sync_date"), ("dim", F_DIM, "sync_dim"), ("region", F_REGION, "sync_region"),
                    ("ou", F_OU, "sync_ou"), ("rule", F_RULE, "sync_rule")])
cw = 238
for i, (k, m) in enumerate([("c1", "DQ Score % (Latest)"), ("c2", "DQ Score Change (pp)"),
                            ("c3", "Failing Records (Current)"), ("c4", "Records Failing > 30 Days"),
                            ("c5", "Rules Errored (Latest)")]):
    v.append(card(p, k, 20 + i * (cw + 12.5), 128, cw, 96, m, 200 + i))
v.append(visual(p, "bar_dim", 20, 236, 545, 206, "clusteredBarChart",
                roles={"Category": [F_DIM], "Y": [meas("DQ Score % (Latest)")]},
                title="DQ score by dimension (latest run)", z=300))
v.append(visual(p, "line_trend", 577, 236, 683, 206, "lineChart",
                roles={"Category": [F_DATE], "Y": [meas("DQ Score %")]},
                title="DQ score trend", z=301))
fr_latest = meas("Failed Records (Latest)")
v.append(visual(p, "tbl_top", 20, 454, 1050, 250, "tableEx",
                roles={"Values": [col("dq_rule_catalog", "rule_name"), col("dq_rule_catalog", "dimension_name"),
                                  col("dq_rule_catalog", "severity"), fr_latest,
                                  meas("DQ Score % (Latest)"), meas("DQ Score Change (pp)")]},
                sort=(fr_latest, "Descending"), title="Failing rules (latest run)", z=302))
v.append(textbox(p, "sp_link", 1082, 454, 178, 120,
                 [run("Open failed-record files (SharePoint)", "11pt", True, "#1D4ED8", url=SP_URL)],
                 fill="#FFFFFF", z=303))
pages.append((p, "Overview", v))

# 2. DQ Trend
p = "Trend"
v = header(p, "DQ Trend")
v += slicer_row(p, [("date", F_DATE, "sync_date"), ("dim", F_DIM, "sync_dim"), ("region", F_REGION, "sync_region"),
                    ("ou", F_OU, "sync_ou"), ("sev", F_SEV, "sync_sev")])
v.append(visual(p, "line_main", 20, 128, 1240, 300, "lineChart",
                roles={"Category": [F_DATE], "Y": [meas("DQ Score %"), meas("DQ Score % (Rule Avg)")]},
                title="Overall DQ score by day (record-weighted vs rule average)", z=200))
v.append(visual(p, "col_rules", 20, 440, 610, 264, "clusteredColumnChart",
                roles={"Category": [F_DATE], "Y": [meas("Rules Executed")]},
                title="Rules executed by day (explains jumps in the score)", z=201))
v.append(visual(p, "line_dim", 642, 440, 618, 264, "lineChart",
                roles={"Category": [F_DATE], "Y": [meas("DQ Score %")], "Series": [F_DIM]},
                title="DQ score by dimension, by day", z=202))
pages.append((p, "DQ Trend", v))

# 3. Rule Audit  (no OU slicers: audit columns are per run, not per OU)
p = "RuleAudit"
v = header(p, "Rule Audit")
v += slicer_row(p, [("date", F_DATE, "sync_date"), ("status", col("dq_rule_run_log", "status"), "sync_status"),
                    ("dim", F_DIM, "sync_dim"), ("rule", F_RULE, "sync_rule"), ("sev", F_SEV, "sync_sev")])
v.append(card(p, "c_exec", 20, 128, 300, 92, "Rules Executed", 200))
v.append(card(p, "c_err", 332, 128, 300, 92, "Rules Errored", 201))
rl_date = col("dq_rule_run_log", "run_date")
v.append(visual(p, "tbl_audit", 20, 232, 1240, 472, "tableEx",
                roles={"Values": [rl_date, col("dq_rule_run_log", "rule_id"),
                                  col("dq_rule_catalog", "rule_name"), col("dq_rule_catalog", "rule_description"),
                                  col("dq_rule_catalog", "dimension_name"), col("dq_rule_run_log", "rule_version"),
                                  col("dq_rule_run_log", "status"), col("dq_rule_run_log", "total_count"),
                                  col("dq_rule_run_log", "failed_count"), col("dq_rule_run_log", "pass_rate"),
                                  col("dq_rule_run_log", "duration_sec"), col("dq_rule_run_log", "error_message")]},
                sort=(rl_date, "Descending"), title="Rule run log", z=202))
pages.append((p, "Rule Audit", v))

# 4. Failed Records
p = "FailedRecords"
v = header(p, "Failed Records")
v += slicer_row(p, [("acct", col("dq_failed_records_current", "account_number"), "sync_acct"),
                    ("site", col("dq_failed_records_current", "cust_acct_site_id"), "sync_site"),
                    ("dim", F_DIM, "sync_dim"), ("rule", F_RULE, "sync_rule"), ("ou", F_OU, "sync_ou")])
v.append(card(p, "c_fail", 20, 128, 300, 92, "Failing Records (Current)", 200))
v.append(card(p, "c_30", 332, 128, 300, 92, "Records Failing > 30 Days", 201))
v.append(textbox(p, "sp_link", 644, 128, 616, 92,
                 [run("Download full lists – one CSV per rule (SharePoint)", "12pt", True, "#1D4ED8", url=SP_URL),
                  run("   Files list every row a rule's query returns; counts here are distinct records.",
                      "9pt", False, "#4B5563")],
                 fill="#FFFFFF", z=202))
days = col("dq_failed_records_current", "days_failing")
v.append(visual(p, "tbl_records", 20, 232, 1240, 472, "tableEx",
                roles={"Values": [col("dq_rule_catalog", "rule_name"), col("dq_rule_catalog", "dimension_name"),
                                  col("dq_failed_records_current", "record_key"),
                                  col("dq_failed_records_current", "account_number"),
                                  col("dq_failed_records_current", "party_number"),
                                  col("dq_failed_records_current", "cust_acct_site_id"),
                                  F_OU, F_REGION,
                                  col("dq_failed_records_current", "first_failed_date"), days]},
                sort=(days, "Descending"), title="Records to fix (latest run)", z=203))
pages.append((p, "Failed Records", v))

# ------------------------------------------------------------------ write
if os.path.exists(REPORT_DIR):
    shutil.rmtree(REPORT_DIR)

def w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

w(f"{ROOT}/{REPORT_NAME}.pbip", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0",
    "artifacts": [{"report": {"path": f"{REPORT_NAME}.Report"}}],
    "settings": {"enableAutoRecovery": True}})

w(f"{REPORT_DIR}/definition.pbir", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byConnection": {"connectionString":
        "Data Source=\"powerbi://api.powerbi.com/v1.0/myorg/[WorkspaceName]\";initial catalog=SM_DQ_Customer;"
        "access mode=readonly;integrated security=ClaimsToken;semanticmodelid=[SemanticModelId]"}}})

w(f"{REPORT_DIR}/.platform", {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": "DQ Dashboard"},
    "config": {"version": "2.0", "logicalId": str(uuid.UUID(hid("dq-dashboard-logical-id", n=32)))}})

w(f"{DEF}/version.json", {"$schema": SCHEMA["version"], "version": "2.0.0"})

page_ids = [hid("page", p) for p, _, _ in pages]
w(f"{DEF}/report.json", {
    "$schema": SCHEMA["report"],
    "themeCollection": {"baseTheme": {"name": "CY24SU06", "reportVersionAtImport": "5.55", "type": "SharedResources"}},
    "layoutOptimization": "None"})
w(f"{DEF}/pages/pages.json", {"$schema": SCHEMA["pages"], "pageOrder": page_ids, "activePageName": page_ids[0]})

for (p, display, visuals), pid in zip(pages, page_ids):
    w(f"{DEF}/pages/{pid}/page.json", {
        "$schema": SCHEMA["page"], "name": pid, "displayName": display, "displayOption": "FitToPage",
        "height": 720, "width": 1280,
        "objects": {"background": [{"properties": {"color": color("#F3F5F8"), "transparency": num(0)}}]}})
    for name, obj in visuals:
        w(f"{DEF}/pages/{pid}/visuals/{name}/visual.json", obj)

print("pages:", [(d, len(v)) for _, d, v in pages])
