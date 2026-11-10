"""Write synthetic test data: N clients with random line items, plus one bad row (missing period_start).
Usage: python tests/make_test_data.py [N]      -> tests/data/clients.csv, tests/data/line_items.csv
Uses a fixed random seed so runs are repeatable. Names and IDs are made up."""
import csv, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")

FIRST = ["Jane", "Mary", "John", "Peter", "Helen", "Margaret", "Robert", "Joan", "Barry", "Elaine", "Ken", "Dorothy"]
LAST = ["Smith", "Nguyen", "Brown", "Wilson", "Taylor", "Kelly", "Martin", "Rossi", "Singh", "Walker", "Young", "Lee"]
TOWNS = [("Sampletown", "SA", 5000), ("Testville", "VIC", 3000), ("Exampleton", "NSW", 2000), ("Demoburn", "QLD", 4000)]
SAH_SERVICES = [("Personal care", "Assistance with self-care and activities of daily living", 100),
                ("Domestic assistance", "General house cleaning", 95),
                ("Respite", "Third party supplier: Respite care", 99),
                ("Nursing care", "Nursing care - wound management", 140),
                ("Allied health and other therapeutic services", "Physiotherapy", 160),
                ("Meals", "Meal preparation", 80),
                ("Home maintenance and repairs", "Garden maintenance", 90)]
AT_ITEMS = [("Equipment and products", "Shower chair", 180), ("Prescription", "OT assessment for equipment", 200),
            ("Repairs and maintenance", "Walker repair", 60)]
HM_ITEMS = [("Home modifications", "Grab rail installation", 350), ("Prescription", "OT home assessment", 220),
            ("Coordination costs", "Builder coordination", 120)]
RC_ITEMS = [("Allied health and other therapeutic services", "Physiotherapy - restorative", 160),
            ("Personal care", "Personal care - restorative", 100)]


# Column order of clients.csv. Kept here because client CSVs are not stored in the repo.
CLIENT_HEADER = ("client_id,title_name,addr1,addr2,addr3,country,provider_id,location,period_start,period_end,quarter,"
                 "month_in_quarter,provider_phone,provider_hours,provider_email,sah_quarterly_budget,veterans_supplement,"
                 "sah_unspent_funds,sah_prior_spend,hcp_cw_start,hcp_notional_start,hcp_cr_start,hcp_cw_end,hcp_notional_end,"
                 "hcp_cr_end,at_tier,at_budget,at_remote_supp,at_additional,at_dogs,at_prior_spend,at_expiry,hm_tier,hm_budget,"
                 "hm_remote_supp,hm_prior_spend,hm_expiry,rc_start,rc_end,rc_budget,rc_primary_supp,rc_prior_spend").split(",")


def item(cid, section, status, date, cat, desc, units, cost):
    gov = round(units * cost * 0.95, 2) if section not in ("CARE_MGMT",) else ""
    con = round(units * cost * 0.05, 2) if gov != "" else ""
    return dict(client_id=cid, section=section, status=status, date=date, category=cat, description=desc,
                rate="Per hour" if section in ("SAH", "RC", "CARE_MGMT") else "Per item",
                units=units, unit_cost=cost if section != "CARE_MGMT" else "", gov_subsidy=gov, contribution=con)


def main(n=1000):
    rnd = random.Random(12345)
    os.makedirs(OUT, exist_ok=True)
    header = CLIENT_HEADER
    clients, items = [], []
    for i in range(1, n + 1):
        cid = f"TC{i:05d}"
        town, state, pc = rnd.choice(TOWNS)
        c = dict.fromkeys(header, "")
        c.update(client_id=cid, title_name=f"{rnd.choice(['Mr', 'Mrs', 'Ms'])} {rnd.choice(FIRST)} {rnd.choice(LAST)}",
                 addr1=f"{rnd.randint(1, 200)} Test Street", addr2=f"{town} {state} {pc}", country="Australia",
                 provider_id="67890", location=f"{town} {state}", period_start="01-10-2026", period_end="31-10-2026",
                 quarter="2", month_in_quarter="1", provider_phone="1800 123 456",
                 provider_hours="Monday to Friday 8:30am to 5:00pm", provider_email="information@example.com.au",
                 sah_quarterly_budget=rnd.choice([3050, 4500, 6200, 8800]), sah_unspent_funds=rnd.choice(["", 470, 1000]))
        items.append(item(cid, "CARE_MGMT", "delivered", "", "Care management", "Care management", rnd.randint(1, 4), ""))
        for _ in range(rnd.randint(3, 25)):
            cat, desc, cost = rnd.choice(SAH_SERVICES)
            items.append(item(cid, "SAH", "delivered", f"{rnd.randint(1, 31):02d}-10-2026", cat, desc, rnd.choice([0.5, 1, 1.5, 2, 3]), cost))
        if rnd.random() < 0.3:
            c.update(at_tier="AT short-term - high tier", at_budget=15000, at_expiry="15-11-2026")
            for _ in range(rnd.randint(1, 5)):
                cat, desc, cost = rnd.choice(AT_ITEMS)
                items.append(item(cid, "AT", rnd.choice(["delivered", "committed"]), f"{rnd.randint(1, 31):02d}-10-2026", cat, desc, 1, cost))
        if rnd.random() < 0.2:
            c.update(hm_tier="HM short-term - high tier", hm_budget=15000, hm_expiry="15-11-2026")
            for _ in range(rnd.randint(1, 4)):
                cat, desc, cost = rnd.choice(HM_ITEMS)
                items.append(item(cid, "HM", rnd.choice(["delivered", "committed"]), f"{rnd.randint(1, 31):02d}-10-2026", cat, desc, 1, cost))
        if rnd.random() < 0.1:
            c.update(rc_start="01-10-2026", rc_end="25-12-2026", rc_budget=6000)   # starts 1 Oct, so no prior spend
            for _ in range(rnd.randint(2, 8)):
                cat, desc, cost = rnd.choice(RC_ITEMS)
                items.append(item(cid, "RC", "delivered", f"{rnd.randint(1, 31):02d}-10-2026", cat, desc, 1, cost))
        clients.append(c)
    # One deliberately bad row, in the middle of the file.
    clients[n // 2]["period_start"] = ""
    with open(os.path.join(OUT, "clients.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header); w.writeheader(); w.writerows(clients)
    with open(os.path.join(OUT, "line_items.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(items[0])); w.writeheader(); w.writerows(items)
    print(f"Wrote {n} clients ({len(items)} line items) to {OUT}; bad row: {clients[n // 2]['client_id']} (no period_start)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
