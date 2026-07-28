# build_jsonld.py
# This script reads the UN Ocean Decade Actions dtabase (Excel file) and creates JSON-LD files (machine-readable data) for each project, programme, and #contribution.

import pandas as pd
import pystache
import json
import os
from datetime import datetime, timezone


EXCEL_PATH = r"C:\Users\MargaritaLopez\Desktop\OceanDecadeActions.xlsx"
TEMPLATE_PATH = "template.mustache"
OUTPUT_DIR = "docs"         
COMBINED_FILE = "ocean_decade_actions.jsonld"

# pURL base for each record
PURL_BASE = "https://purl.org/oceandecade/decadeactions/"

# License (Creative Commons Attribution 4.0)
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

# UN Ocean Decade definitions for each Type of Action
ACTION_TYPE_INFO = {
    "Programme": {
        "label": "Decade Programme",
        "description": "A Programme is typically global or regional in scale and "
                       "contributes to the achievement of one or more of the Decade "
                       "Challenges. It is long-term (multi-year), interdisciplinary, "
                       "and consists of component Decade Projects and potentially "
                       "enabling Decade Activities."
    },
    "Project": {
        "label": "Decade Project",
        "description": "A Project is a targeted regional, national, or subnational "
                       "initiative that typically contributes to an identified "
                       "Decade Programme."
    },
    "Contribution": {
        "label": "Decade Contribution",
        "description": "A Contribution is a one-off standalone initiative (such as "
                       "an awareness-raising event, a scientific workshop, a "
                       "training opportunity or a publication). It enables a Decade "
                       "Programme or Project, or directly contributes to a Decade "
                       "Challenge."
    },
}

# Values in "Host Programme" that mean there is no host programme
NO_PROGRAMME_VALUES = ["Not applicable", "Not yet defined"]


# Read Excel file
df = pd.read_excel(EXCEL_PATH)
print(f"Loaded {len(df)} rows from Excel.")


# ID to PURL

id_to_purl = {}
for index, row in df.iterrows():
    record_id = str(row["ID"]).strip()
    id_to_purl[record_id] = PURL_BASE + record_id


# Load Mustache template

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    template_text = f.read()


# Confirm output folder exists

os.makedirs(OUTPUT_DIR, exist_ok=True)


# build its JSON-LD

all_records = []  # I'll collect every record here for the combined file

for index, row in df.iterrows():

    record_id        = str(row["ID"]).strip()
    name             = str(row["Name of the Proposal"]).strip()
    action_type      = str(row["Type of Action"]).strip()
    lead_institution = str(row["Lead Institution"]).strip()
    country          = str(row["Country"]).strip()
    summary = " ".join(str(row["Summary"]).strip().splitlines())
    host_programme_text = str(row["Host Programme"]).strip()
    human_url        = str(row["Link"]).strip()  # real webpage for humans

    # Build this record's permanent PURL identifier
    purl_id = PURL_BASE + record_id

    # Check the Type of Action
    if action_type not in ACTION_TYPE_INFO:
        print(f"  WARNING: row with ID '{record_id}' has an unknown "
              f"Type of Action ('{action_type}'). Skipping this row.")
        continue

    type_label       = ACTION_TYPE_INFO[action_type]["label"]
    type_description = ACTION_TYPE_INFO[action_type]["description"]

       # Host programme issue

    has_host_programme = False
    host_programme_url = ""

    if host_programme_text in NO_PROGRAMME_VALUES:
       
        has_host_programme = False

    else:

        if " " in host_programme_text:
            possible_id = host_programme_text.split(" ", 1)[0]
        else:
            possible_id = host_programme_text

        possible_id = possible_id.strip().rstrip(".") 

        if possible_id in id_to_purl:
            has_host_programme = True
            host_programme_url = id_to_purl[possible_id]  # link to its PURL new addition
        else:
            print(f"  WARNING: could not match Host Programme text "
                  f"'{host_programme_text}' (extracted ID: '{possible_id}')")
            has_host_programme = False

    
    # Fill in the Mustache template for this row
   
    template_data = {
        "purl_id":                purl_id,
        "name":                   name,
        "summary":                summary,
        "country":                country,
        "id":                     record_id,
        "human_url":              human_url,
        "lead_institution":       lead_institution,
        "action_type_label":      type_label,
        "action_type_description": type_description,
        "has_host_programme":     has_host_programme,
        "host_programme_url":     host_programme_url,
    }

    filled_template = pystache.render(template_text, template_data)

    # Save as docs/UN1.jsonld for github
    output_path = os.path.join(OUTPUT_DIR, f"{record_id}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(filled_template)

    
    record_dict = {
        "@id": purl_id,
        "@type": ["foaf:Project", "sdo:Project"],
        "foaf:name": name,
        "sdo:name": name,
        "sdo:description": summary,
        "sdo:location": country,
        "sdo:identifier": record_id,
        "sdo:url": human_url,
        "sdo:license": LICENSE_URL,
        "sdo:parentOrganization": {
            "@type": "sdo:Organization",
            "sdo:name": lead_institution
        },
        "sdo:keywords": [
            {
                "@type": "sdo:DefinedTerm",
                "sdo:name": type_label,
                "sdo:description": type_description,
                "sdo:inDefinedTermSet": {
                    "@type": "sdo:DefinedTermSet",
                    "sdo:name": "UN Ocean Decade Action types.",
                    "sdo:description": "A definition of the types of Decade Action."
                }
            }
        ]
    }

    if has_host_programme:
        record_dict["sdo:memberOf"] = {"@id": host_programme_url}

    all_records.append(record_dict)

print(f"\nFinished. {len(all_records)} records saved to '{OUTPUT_DIR}' folder.")


# STEP 6: Build the single combined JSON-LD 

combined_data = {
    "@context": [
        {"foaf": "://xmlns.com/foaf/0.1/"},
        {"sdo": "s://schema.org/"}
    ],
    "sdo:dateModified": datetime.now(timezone.utc).date().isoformat(),
    "sdo:license": LICENSE_URL,
    "@graph": all_records
}

with open(COMBINED_FILE, "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)

print(f"Combined graph file saved as: {COMBINED_FILE}")
