
"""Support at Home monthly statement generator (POC).
Usage (from the main folder): py app/sah_statement.py clients.csv line_items.csv output_dir
Requires: reportlab (BSD licence)."""
import csv, sys, os, re, time, datetime as dt
from collections import defaultdict
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.utils import ImageReader
from PIL import Image
LOGO=None

PURPLE=colors.HexColor("#6B4C8A"); BLUE=colors.HexColor("#00539B"); DARK=colors.HexColor("#4A3B6B")
NAVY=colors.HexColor("#221A4C"); SUB=colors.HexColor("#C8CCE3"); ALT1=colors.HexColor("#E2E4F0")
ALT2=colors.HexColor("#F0F2F7"); GREY=colors.HexColor("#F1F1F1")
BAR1=colors.HexColor("#8068A0"); BAR2=colors.HexColor("#93B3D3"); BAR3=colors.HexColor("#7BBDBD")
W,H=A4; LM=RM=15*mm; CW=W-LM-RM

def ps(n,size=9.5,bold=False,col=colors.black,al=0,lead=None):
    return ParagraphStyle(n,fontName="Helvetica-Bold" if bold else "Helvetica",fontSize=size,leading=lead or size*1.25,textColor=col,alignment=al)
TITLE=ps("t",22,True,PURPLE); H1=ps("h1",15,True,PURPLE); H2=ps("h2",12.5,True,PURPLE)
BODY=ps("b",10.5); CELL=ps("c",9); CELLB=ps("cb",9,True); WH=ps("w",9,True,colors.white)
WHR=ps("wr",9,True,colors.white,2); CELLR=ps("cr",9,al=2); SUBR=ps("sr",9,True,al=2)
ITAL=ParagraphStyle("i",parent=BODY,fontName="Helvetica-Oblique")

def num(v):
    v=(v or "").strip().replace("$","").replace(",","")
    return float(v) if v else None
def money(v):
    if v is None: return "N/A"
    s="${:,.2f}".format(abs(v)); return "-"+s if round(v,2)<0 else s
def na(v): return money(v) if v else "N/A"
def d(v): return dt.date.fromisoformat(v) if v else None
def longd(x): return f"{x.day} {x:%B %Y}"
def shortd(v):
    if not v: return "To be delivered"
    x=d(v); return f"{['Mon','Tues','Wed','Thurs','Fri','Sat','Sun'][x.weekday()]}, {x.day} {x:%b}"

def summary_table(rows):
    data=[]; st=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),1.8),("BOTTOMPADDING",(0,0),(-1,-1),1.8)]
    for i,(l,v,k) in enumerate(rows):
        if k in("head","total"):
            data.append([Paragraph(l,WH),Paragraph(v,WHR)]); st.append(("BACKGROUND",(0,i),(-1,i),BLUE if k=="head" else DARK))
        elif k=="sub":
            data.append([Paragraph(l,CELLB),Paragraph(v,SUBR)]); st.append(("BACKGROUND",(0,i),(-1,i),SUB))
        else:
            data.append([Paragraph(("&nbsp;"*6 if k=="indent" else "")+l,CELL),Paragraph(v,CELLR)])
            st+= [("BACKGROUND",(0,i),(-1,i),ALT2),("LINEBELOW",(0,i),(-1,i),0.4,colors.white)]
    t=Table(data,colWidths=[CW*0.78,CW*0.22]); t.setStyle(TableStyle(st)); return t

def detail_table(items,title_col="Service",with_budget=False):
    hdr=["Date"]+(["AT or HM budget"] if with_budget else [])+[title_col,"Rate","Units","Unit cost","Cost","Gov subsidy","Contribution"]
    base=[16,18,32,15,11,17,18,18,20] if with_budget else [19,40,17,11,19,20,20,22]
    widths=[CW*b/sum(base) for b in base]; n=len(hdr); firstnum=n-5
    data=[[Paragraph(h,WHR if j>=firstnum else WH) for j,h in enumerate(hdr)]]
    st=[("BACKGROUND",(0,0),(-1,0),BLUE),("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]
    def block(rows):
        tc=tg=tcon=0
        for r in rows:
            tc+=r["cost"]; tg+=r["gov"]; tcon+=r["con"]
            row=[Paragraph(shortd(r["date"]),CELLB)]
            if with_budget: row.append(Paragraph("Assistive Technology" if r["section"]=="AT_ADJ" else "Home Modifications",CELL))
            row+= [Paragraph(r["description"],CELL),Paragraph(r["rate"],CELL),Paragraph(f'{r["units"]:g}',CELLR),
                   Paragraph(money(r["unit_cost"]),CELLR),Paragraph(money(r["cost"]),CELLR),Paragraph(money(r["gov"]),CELLR),Paragraph(money(r["con"]),CELLR)]
            i=len(data); data.append(row); st.append(("BACKGROUND",(0,i),(-1,i),ALT1 if i%2 else ALT2))
        i=len(data)
        data.append([Paragraph("Total",WH)]+[""]*(n-4)+[Paragraph(money(tc),WHR),Paragraph(money(tg),WHR),Paragraph(money(tcon),WHR)])
        st.append(("BACKGROUND",(0,i),(-1,i),BLUE))
    dl=[r for r in items if r["status"]!="committed"]; cm=[r for r in items if r["status"]=="committed"]
    if dl: block(dl)
    if cm: block(cm)
    t=Table(data,colWidths=widths,repeatRows=1); t.setStyle(TableStyle(st)); return t

def chart(title,labels,values,cols,w=CW*0.46,h=58*mm):
    dr=Drawing(w,h); bc=VerticalBarChart(); bc.x=8; bc.y=32; bc.width=w-16; bc.height=h-54
    bc.data=[values]; bc.valueAxis.valueMin=0; bc.valueAxis.valueMax=max(values+[1])*1.12; bc.valueAxis.visible=False
    bc.categoryAxis.categoryNames=["\n".join(l.split(" ",2)) for l in labels]
    bc.categoryAxis.labels.fontSize=7.5; bc.categoryAxis.labels.dy=-2; bc.barSpacing=6; bc.groupSpacing=14
    for i,cl in enumerate(cols): bc.bars[(0,i)].fillColor=cl; bc.bars[(0,i)].strokeColor=None
    bc.barLabelFormat=lambda v:"${:,.2f}".format(v) if v%1 else "${:,.0f}".format(v)
    bc.barLabels.fontName="Helvetica-Bold"; bc.barLabels.fontSize=7.5; bc.barLabels.nudge=6
    dr.add(bc); dr.add(String(w/2,h-10,title,fontName="Helvetica-Bold",fontSize=9.5,textAnchor="middle")); return dr

HDR=20*mm   # header bar height (all pages)
def header(c,first=False):
    """Thin grey bar: provider name, address and contacts on the left (or 'Support at Home' if there's no
    provider.csv), provider logo (square) on the right."""
    c.setFillColor(GREY); c.rect(0,H-HDR,W,HDR,0,1)
    s=HDR-4*mm
    if PROVIDER: provider_block(c,LM,W-RM-(s+6*mm if LOGO else 0))
    else:
        c.setFillColor(BLUE); c.setFont("Helvetica-Bold",17); c.drawString(LM,H-HDR/2-1*mm,"Support")
        c.setFillColor(PURPLE); c.setFont("Helvetica",17); c.drawString(LM+c.stringWidth("Support ","Helvetica-Bold",17),H-HDR/2-1*mm,"at Home")
    if LOGO:
        c.drawImage(LOGO,W-RM-s,H-HDR+2*mm,width=s,height=s,preserveAspectRatio=True,anchor="e",mask="auto")
    if first:
        for i,cl in enumerate(["#8068A0","#93B3D3","#7BBDBD","#8E5BA8","#4FA8A8","#00539B","#221A4C"]):
            c.setFillColor(colors.HexColor(cl)); c.rect(i*W/7,H-HDR-2.5*mm,W/7,2.5*mm,0,1)

def provider_block(c,left,right):
    """Provider name, address and contacts, left-aligned between x=left and x=right, centred in the header bar."""
    p=PROVIDER; addr=", ".join(x for x in(p["addr1"],p["addr2"],p["addr3"]) if x)
    contact="   ".join(x for x in(p["phone"] and "Phone "+p["phone"],p["email"]) if x)
    extra="   ".join(x for x in(p["website"],p["abn"] and "ABN "+p["abn"]) if x)
    lines=[(p["provider_name"],"Helvetica-Bold",12,BLUE)]+[(t,"Helvetica",8,colors.HexColor("#444444")) for t in(addr,contact,extra) if t]
    fit=[]
    for t,font,size,col in lines:
        while size>5.5 and c.stringWidth(t,font,size)>right-left: size-=0.25   # shrink long lines to fit
        fit.append((t,font,size,col))
    # Centre the visible text (cap height of the first line to descenders of the last), not the line boxes.
    gaps=[0.22*a[2]+0.72*b[2]+2.5 for a,b in zip(fit,fit[1:])]; tall=0.72*fit[0][2]+sum(gaps)+0.22*fit[-1][2]
    y=H-HDR/2+tall/2-0.72*fit[0][2]
    for (t,font,size,col),gap in zip(fit,gaps+[0]):
        c.setFillColor(col); c.setFont(font,size); c.drawString(left,y,t); y-=gap

MIN_PX,MIN_RATIO,MAX_RATIO=300,0.8,1.25
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # main folder (this file lives in app)
BRANDING=os.path.join(ROOT,"branding")
class BrandingError(Exception):
    """Something in the branding folder can't be used. str(e) is a plain-English message."""
class LogoError(BrandingError): pass
class ProviderError(BrandingError): pass

PROVIDER=None
PROVIDER_COLS=["provider_name","addr1","addr2","addr3","phone","email","website","abn"]
def load_provider(folder=BRANDING):
    """Read branding/provider.csv (one row) for the page header. Missing = header without provider details;
    unusable = raise ProviderError. Returns the status line to show the user."""
    global PROVIDER
    PROVIDER=None
    path=os.path.join(folder,"provider.csv")
    if not os.path.exists(path): return f"No provider.csv found in {folder} - header will show the logo only."
    try:
        with open(path,newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    except UnicodeDecodeError: raise ProviderError(f"Provider details error: {path} isn't saved as UTF-8. In Excel use Save As > 'CSV UTF-8 (Comma delimited)'.")
    except (OSError,csv.Error) as ex: raise ProviderError(f"Provider details error: {path} can't be read ({ex}). If it's open in Excel, close it.")
    if not rows or "provider_name" not in rows[0]: raise ProviderError(f"Provider details error: {path} needs a provider_name column and one row of details.")
    p={k:(rows[0].get(k) or "").strip() for k in PROVIDER_COLS}
    if not p["provider_name"]: raise ProviderError(f"Provider details error: provider_name is empty in {path}.")
    PROVIDER=p; return f"Provider details OK: {p['provider_name']}"

def load_logo(folder=BRANDING):
    """Validate the provider logo (branding/logo.png or .jpg). Missing = no logo; invalid = raise LogoError.
    Returns the status line to show the user."""
    global LOGO
    LOGO=None
    path=next((os.path.join(folder,n) for n in("logo.png","logo.jpg","logo.jpeg") if os.path.exists(os.path.join(folder,n))),None)
    if not path: return f"No logo found in {folder} - statements will be built without one."
    try:
        with Image.open(path) as im: im.verify()
        with Image.open(path) as im: fmt,(w,h)=im.format,im.size
    except Exception: raise LogoError(f"Logo error: {path} is not a readable image file.")
    if fmt not in("PNG","JPEG"): raise LogoError(f"Logo error: logo must be PNG or JPG (got {fmt}).")
    if w<MIN_PX or h<MIN_PX: raise LogoError(f"Logo error: logo must be at least {MIN_PX} x {MIN_PX} pixels (got {w} x {h}).")
    if not MIN_RATIO<=w/h<=MAX_RATIO: raise LogoError(f"Logo error: logo must be roughly square (got {w} x {h}).")
    LOGO=ImageReader(path); return f"Logo OK: {path} ({w} x {h})"

def first_page(c,doc): c.saveState(); header(c,True); c.restoreState()
def later_page(c,doc): c.saveState(); header(c); c.restoreState()

def build(client,items,out):
    g=defaultdict(list)
    for r in items:
        u=num(r["units"]) or 0; uc=num(r["unit_cost"])
        r.update(units=u,unit_cost=uc,cost=round(u*(uc or 0),2),gov=num(r["gov_subsidy"]) or 0,con=num(r["contribution"]) or 0)
        g[r["section"]].append(r)
    for k in g: g[k].sort(key=lambda r:(r["status"]=="committed",r["date"] or "9"))
    C=lambda k:num(client.get(k)); Z=lambda k:C(k) or 0
    s=lambda k:sum(r["cost"] for r in g[k] if r["status"]!="committed")
    com=lambda k:sum(r["cost"] for r in g[k] if r["status"]=="committed")
    def cat(keys,name,sign=-1):
        v=sum(r["cost"] for k in keys for r in g[k] if r["category"]==name and r["status"]!="committed")
        return money(sign*v) if v else "N/A"
    p0,p1=d(client["period_start"]),d(client["period_end"]); mon=p0.strftime("%b"); miq=int(client["month_in_quarter"])
    qm=[(p0.month-miq+i)%12+1 for i in range(3)]; mn=lambda m:dt.date(2000,m,1).strftime("%b")
    qyear=p0.year if qm[2]>=p0.month else p0.year+1
    sd,ed=longd(p0),longd(p1)
    period=f'Statement calendar month {miq} quarter {client["quarter"]}: {sd} to {ed}'
    avail=Z("sah_quarterly_budget")+Z("veterans_supplement")+Z("sah_unspent_funds")-Z("sah_prior_spend")
    deliv=s("SAH"); adj=s("SAH_ADJ"); rem=avail-deliv-adj
    at_av=Z("at_budget")+Z("at_remote_supp")+Z("at_additional")+Z("at_dogs")-Z("at_prior_spend")
    at_d=s("AT"); at_adj=s("AT_ADJ"); at_rem=at_av-at_d-at_adj; at_c=com("AT")
    hm_av=Z("hm_budget")+Z("hm_remote_supp")-Z("hm_prior_spend")
    hm_d=s("HM"); hm_adj=s("HM_ADJ"); hm_rem=hm_av-hm_d-hm_adj; hm_c=com("HM")
    rc_on=bool(C("rc_budget")); rc_av=Z("rc_budget")+Z("rc_primary_supp")-Z("rc_prior_spend")
    rc_d=s("RC"); rc_m=s("RC_MGMT"); rc_rem=rc_av-rc_d-rc_m
    st=[Spacer(1,1),Paragraph("Support at Home monthly statement",TITLE),Spacer(1,4*mm),
        Paragraph("Statement provided to:",ps("sp",14,col=PURPLE)),Spacer(1,3*mm)]
    addr="<br/>".join(x for x in [client["title_name"],client["addr1"],client["addr2"],client["addr3"],client["country"]] if x)
    info=Table([[Paragraph(a,BODY),Paragraph(b,BODY)] for a,b in [("<b>Client Name:</b>",client["title_name"]),
        ("<b>My Aged Care ID No:</b>",client["client_id"]),("<b>Provider ID:</b>",client["provider_id"]),("<b>Location:</b>",client["location"])]],
        colWidths=[CW*0.27,CW*0.25],style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)])
    st.append(Table([[Paragraph(addr,ps("ad",10.5,lead=14)),info]],colWidths=[CW*0.48,CW*0.52],style=[("VALIGN",(0,0),(-1,-1),"TOP")]))
    box=Table([[Paragraph("This is not an invoice – no payment is required.",ps("n",12,True))],
        [Paragraph("This statement includes information relating to the services you received in the previous calendar month.<br/>"
                   "Please review this statement and discuss any concerns with your provider.<br/>"
                   "You will receive a separate invoice relating to payment of participant contributions.",BODY)],
        [Paragraph(f'<b>{client["provider_phone"]} {client["provider_hours"]}</b>&nbsp;&nbsp;&nbsp;&nbsp;<b>{client["provider_email"]}</b>',BODY)]],
        colWidths=[CW],style=[("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F2F7F8")),("BOX",(0,0),(-1,-1),0.6,BAR3),("LEFTPADDING",(0,0),(-1,-1),8)])
    st+= [Spacer(1,4*mm),box,Spacer(1,4*mm),Paragraph(f"Financial summary {p0:%B %Y}",H2),Spacer(1,2*mm)]
    rest="-".join(mn(m) for m in qm[miq:]) if miq<3 else "next quarter"
    ch=[chart(f"Services Budget {mn(qm[0])}-{mn(qm[2])} {qyear}",[f"{mon} expenditure",f"Available balance {rest}"],[deliv+adj,rem],[BAR1,BAR2]),"","",""]
    if C("at_budget"): ch[1]=chart("Assistive Technology Budget",[f"{mon} expenditure","Committed assistive technology funds",f"Remaining budget {longd(d(client['at_expiry']))}"],[at_d+at_adj,at_c,at_rem-at_c],[BAR1,BAR2,BAR3])
    if C("hm_budget"): ch[2]=chart("Home Modification Budget",[f"{mon} expenditure","Committed home modification funds",f"Remaining budget {longd(d(client['hm_expiry']))}"],[hm_d+hm_adj,hm_c,hm_rem-hm_c],[BAR1,BAR2,BAR3])
    if rc_on: ch[3]=chart("Restorative Care Budget",["Spending from previous month(s)",f"{mon} expenditure",f"Remaining budget {longd(d(client['rc_end']))}"],[Z("rc_prior_spend"),rc_d+rc_m,rc_rem],[BAR1,BAR2,BAR3])
    st+= [Table([[ch[0],ch[1]],[ch[2],ch[3]]],colWidths=[CW/2]*2),
          Paragraph("Note: Government subsidy and contribution rate calculated at the full pensioner rate for this template.",ps("nt",8.5)),PageBreak()]
    st+= [Paragraph("Support at Home ongoing budget",H1),Paragraph("Support at Home account summary",H2),Spacer(1,2*mm),Paragraph(period,BODY),Spacer(1,2*mm),
      summary_table([("Support at Home quarterly budget",money(C("sah_quarterly_budget")),"head"),("Primary supplement(s) (if applicable)","","line"),
        ("Veterans’ supplement",na(C("veterans_supplement")),"indent"),("Support at Home unspent funds",na(C("sah_unspent_funds")),"line"),
        ("Spending from past month(s) in the same quarter",na(C("sah_prior_spend")),"line"),(f"Available budget on {sd}",money(avail),"total")]),Spacer(1,4*mm),
      summary_table([(f"Quarterly budget balance on {sd}",money(avail),"head"),("Services delivered (including your contributions)",money(deliv),"indent"),
        ("Charges from past months",na(adj),"indent"),(f"Remaining balance as of {ed}",money(rem),"total")]),Spacer(1,6*mm),
      Paragraph("Service type summary",H2),Spacer(1,2*mm)]
    cats=["Nursing care","Allied health and other therapeutic services","Personal care","Respite","Domestic assistance","Home maintenance and repairs","Meals"]
    st+= [summary_table([(f"Budget balance at {sd}",money(avail),"head"),("Service type","Total cost","sub")]+[(c_,cat(["SAH"],c_),"indent") for c_ in cats]+
        [("Adjustments or refunds","","sub"),("Incorrect or missing charges from past months",na(-adj),"indent"),
         (f"Remaining Support at Home quarterly balance as at {ed}",money(rem),"head")]),PageBreak(),
        Paragraph("Detailed expenses",H2),Spacer(1,2*mm)]
    for r in g["CARE_MGMT"]:
        st+= [Table([[Paragraph("Care Management",WH),Paragraph("Rate",WH),Paragraph("Units",WHR)],[Paragraph(r["description"],CELLB),Paragraph(r["rate"],CELLB),Paragraph(f'{r["units"]:g}',CELLR)]],
                colWidths=[CW*0.7,CW*0.18,CW*0.12],style=[("BACKGROUND",(0,0),(-1,0),BLUE),("BACKGROUND",(0,1),(-1,1),SUB)]),Spacer(1,5*mm)]
    if g["SAH"]: st.append(detail_table(g["SAH"]))
    if g["SAH_ADJ"]:
        st+= [Spacer(1,6*mm),Paragraph("Variations from past calendar months",H2),Spacer(1,2*mm),
              Paragraph("The following information relates to any incorrect or missing charges for services or items from past months. Please contact us if you have any concerns or questions.",BODY),
              Spacer(1,2*mm),detail_table(g["SAH_ADJ"])]
    st+= [PageBreak(),Paragraph("Unspent funds",H1),Paragraph("Support at Home unspent funds",H2),Spacer(1,2*mm),
          Paragraph("This information is for your reference only and no action is required from you.",BODY),
          Paragraph("The maximum amount of funds you can carry into the next quarter is $1000 or 10% of your ongoing quarterly budget as a $ figure (whichever is higher).",BODY),Spacer(1,3*mm),
          summary_table([("","Balance as of last quarter","head"),("Unspent funds",na(C("sah_unspent_funds")),"sub")]),Spacer(1,6*mm),
          Paragraph("Unspent funds accrued under Home Care Package program",H1),Spacer(1,2*mm),
          Paragraph("Participants can continue to use HCP Commonwealth unspent funds for Support at Home services.",BODY),Spacer(1,3*mm)]
    for lbl,dd,suf,word in [("HCP Commonwealth unspent funds on",sd,"start","on"),("Available HCP Commonwealth unspent funds as of",ed,"end","as of")]:
        v=[C(f"hcp_cw_{suf}"),C(f"hcp_notional_{suf}"),C(f"hcp_cr_{suf}")]; tot=sum(x for x in v if x) if any(v) else None
        st+= [summary_table([(f"{lbl} {dd}","","head"),("Individual’s unspent Commonwealth portion",na(v[0]),"indent"),
             ("Balance of the individual’s notional home care account",na(v[1]),"indent"),("Individual’s unspent care recipient portion",na(v[2]),"indent"),
             (f"Total available balance {word} {dd}",na(tot),"total")]),Spacer(1,4*mm)]
    if C("at_budget"):
        st+= [PageBreak(),Paragraph("Assistive Technology and Home Modifications (AT-HM) scheme",H1),Paragraph("Assistive Technology account summary",H2),Spacer(1,2*mm),Paragraph(period,BODY),Spacer(1,2*mm),
          summary_table([("Assistive technology budget","","head"),(client["at_tier"],money(C("at_budget")),"line"),("Supplement(s) (if applicable)","","line"),
            ("Remote supplement",na(C("at_remote_supp")),"indent"),("Additional amount approved (if applicable)",na(C("at_additional")),"line"),
            ("AT Ongoing – assistance dogs (ongoing maintenance)",na(C("at_dogs")),"line"),("Spending from past month(s)",na(C("at_prior_spend")),"line"),
            (f"Available budget on {sd}",money(at_av),"sub"),("Assistive technology delivered (including your contributions)",money(-at_d),"line"),
            ("Changes from past months",na(-at_adj),"line"),(f"Remaining balance on {ed}",money(at_rem),"sub"),("Committed funds",money(-at_c),"line"),
            ("Remaining balance for allocation period",money(at_rem-at_c),"total")]),Spacer(1,2*mm),
          Paragraph(f"Assistive technology short-term funding (including supplements and any additional amounts approved) to expire {longd(d(client['at_expiry']))}. Assistive technology ongoing funding will be re-allocated annually.",ITAL),
          Spacer(1,6*mm),Paragraph("Assistive Technology expense summary",H2),Spacer(1,2*mm),
          summary_table([(f"Assistive technology budget as of {sd}",money(at_av),"head")]+[(c_,cat(["AT"],c_),"line") for c_ in
            ["Equipment and products","Prescription","Wraparound services","Repairs and maintenance","Administration costs"]]+
            [("Adjustments or refunds","","sub"),("Incorrect or missing charges from past months",na(-at_adj),"line"),
             (f"Remaining balance on {ed}",money(at_rem),"total"),("Committed funds",money(-at_c),"line"),("Remaining balance for allocation period",money(at_rem-at_c),"total")]),
          PageBreak(),Paragraph("Assistive technology detailed expense information",H2),Spacer(1,2*mm),detail_table(g["AT"])]
        adjs=g["AT_ADJ"]+g["HM_ADJ"]
        if adjs:
            st+= [Spacer(1,6*mm),Paragraph("Adjustments or refunds from past calendar months",H2),Spacer(1,2*mm),
                  Paragraph("The following information relates to any incorrect or missing charges from past months. Please contact us if you have any concerns or questions.",BODY),
                  Spacer(1,2*mm),detail_table([dict(r,cost=abs(r["cost"]),unit_cost=abs(r["unit_cost"] or 0),gov=abs(r["gov"])) for r in adjs],with_budget=True)]
    if C("hm_budget"):
        st+= [PageBreak(),Paragraph("Home modifications account summary",H2),Spacer(1,2*mm),
          summary_table([("Home modifications budget",money(C("hm_budget")),"head"),(client["hm_tier"],money(C("hm_budget")),"line"),("Supplement(s) (if applicable)","","line"),
            ("Remote supplement",na(C("hm_remote_supp")),"indent"),("Spending from past month(s)",na(C("hm_prior_spend")),"line"),
            (f"Available budget on {sd}",money(hm_av),"total"),("Home modifications delivered (including your contributions)",money(-hm_d),"line"),
            ("Changes from past months",money(-hm_adj),"line"),(f"Remaining balance on {ed}",money(hm_rem),"total"),("Committed funds",money(-hm_c),"line"),
            ("Remaining balance for allocation period",money(hm_rem-hm_c),"total")]),Spacer(1,2*mm),
          Paragraph(f"Home modifications funding (including supplements) to expire {longd(d(client['hm_expiry']))}.",ITAL),Spacer(1,6*mm),
          Paragraph("Home Modifications expense summary",H2),Spacer(1,2*mm),
          summary_table([(f"Home modifications budget as of {sd}",money(hm_av),"total")]+[(c_,cat(["HM"],c_),"line") for c_ in
            ["Home modifications","Prescription","Wraparound services","Coordination costs"]]+
            [("Adjustments or refunds","","sub"),("Incorrect or missing charges from past months",na(-hm_adj),"line"),
             (f"Remaining balance on {ed}",money(hm_rem),"head"),("Committed funds (to be delivered)",money(-hm_c),"line"),("Remaining balance for allocation period",money(hm_rem-hm_c),"head")]),
          PageBreak(),Paragraph("Home modifications detailed expense information",H2),Spacer(1,2*mm),detail_table(g["HM"],title_col="Item or service")]
    if rc_on:
        rs,re_=d(client["rc_start"]),d(client["rc_end"])
        st+= [PageBreak(),Paragraph("Restorative Care Pathway",H1),Paragraph("Restorative care summary",H2),Spacer(1,2*mm),
          Paragraph(f"Restorative care started {rs:%B} {rs.day}, {rs.year}. Funding to end {re_:%B} {re_.day}, {re_.year}.",BODY),Spacer(1,2*mm),
          summary_table([("Restorative care budget",money(C("rc_budget")),"head"),("Primary supplement(s) (if applicable)",na(C("rc_primary_supp")),"line"),
            ("Spending from past month(s) within allocated care period",na(-Z("rc_prior_spend")),"line"),
            (f"Available budget on {sd}",money(rc_av),"head"),("Services delivered (including your contributions)",money(rc_d),"indent"),
            ("Restorative care management",na(rc_m),"indent"),("Changes from past months","N/A","indent"),(f"Remaining balance as at {ed}",money(rc_rem),"total")]),Spacer(1,6*mm),
          Paragraph("Restorative care Service type summary",H2),Spacer(1,2*mm)]
        cats_rc=["Nursing care","Allied health and other therapeutic services","Restorative care management","Personal care","Respite","Domestic assistance","Home maintenance and repairs","Meals"]
        st+= [summary_table([(f"Budget balance {sd}",money(rc_av),"head"),("Service type","Total cost","sub")]+[(c_,cat(["RC","RC_MGMT"],c_,1),"line") for c_ in cats_rc]+
              [("Adjustments or refunds","","sub"),("Incorrect or missing charges from past months","N/A","line"),(f"Remaining restorative care balance {ed}",money(rc_rem),"head")]),
              PageBreak(),Paragraph("Restorative care detailed expenses",H2),Spacer(1,2*mm)]
        for r in g["RC_MGMT"]:
            st+= [Table([[Paragraph(h,WH if i<2 else WHR) for i,h in enumerate(["Service","Rate","Units","Unit cost","Cost","Government subsidy"])],
                     [Paragraph(r["description"],CELL),Paragraph(r["rate"],CELL),Paragraph(f'{r["units"]:g}',CELLR),Paragraph(money(r["unit_cost"]),CELLR),Paragraph(money(r["cost"]),CELLR),Paragraph(money(r["gov"]),CELLR)]],
                    colWidths=[CW*x for x in(.4,.13,.1,.12,.12,.13)],style=[("BACKGROUND",(0,0),(-1,0),BLUE),("BACKGROUND",(0,1),(-1,1),ALT1)]),Spacer(1,5*mm)]
        st.append(detail_table(g["RC"]))
    st+= [PageBreak(),Paragraph("For more support",H2),Spacer(1,3*mm),
      Paragraph("Please call or email us if you have any questions regarding your statement or would like to discuss financial or hardship support options.",BODY),Spacer(1,2*mm),
      Paragraph(f'Call: <b>{client["provider_phone"]}</b> {client["provider_hours"]}',BODY),Spacer(1,2*mm),
      Paragraph(f'Email: <b>{client["provider_email"]}</b>',BODY),Spacer(1,5*mm),
      Paragraph("If you have questions or concerns about your aged care, including Support at Home costs and fees, you can speak to an aged care advocate by calling the Aged Care Advocacy Line. Provided by the Older Persons Advocacy Network (OPAN), this free and confidential service is independent of both government and aged care providers, and will connect you with a local advocate in your state or territory.",BODY),Spacer(1,2*mm),
      Paragraph("Aged Care Advocacy Line <b>1800 700 600</b><br/>Monday to Friday – 8:00am-8:00pm<br/>Saturday – 10:00am-4:00pm<br/>Website: <b>www.opan.org.au</b>",BODY),Spacer(1,5*mm),
      Paragraph("If you need assistance in understanding this statement in other languages, you are welcome to access free translation services.",BODY),Spacer(1,2*mm),
      Paragraph("Call: <b>131 450</b> 24 hours, 7 days a week<br/>Website: <b>www.tisnational.gov.au</b>",BODY),Spacer(1,10*mm),
      Table([[Paragraph("<b>Getting started with aged care</b><br/><br/>If you need help around the house or are thinking about aged care homes, contacting My Aged Care is the first step.",ps("g",10.5,col=colors.white,lead=14)),
              Paragraph("<font size=15><b>Freecall 1800 200 422</b></font><br/><br/>Monday to Friday from 8am to 8pm, and Saturdays 10am to 2pm<br/><br/>or face-to-face by speaking with an Aged Care Specialist Officer (to book an appointment call <b>1800 227 475</b> or visit any Services Australia Service Centre).<br/><br/><font size=13><b>MyAgedCare.gov.au</b></font>",ps("g2",9.5,col=colors.white,al=1,lead=13))]],
            colWidths=[CW*0.5,CW*0.5],style=[("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#8A7DB8")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)])]
    # title = file name, so browser tabs and PDF viewers show it instead of "(anonymous)"
    doc=BaseDocTemplate(out,pagesize=A4,leftMargin=LM,rightMargin=RM,topMargin=45*mm,bottomMargin=12*mm,
                        title=os.path.basename(out),author=PROVIDER["provider_name"] if PROVIDER else "",
                        subject="Support at Home monthly statement")
    f1=Frame(LM,12*mm,CW,H-12*mm-HDR-8*mm,id="f1"); f2=Frame(LM,12*mm,CW,H-12*mm-HDR-6*mm,id="f2")
    doc.addPageTemplates([PageTemplate("first",[f1],onPage=first_page,autoNextPageTemplate="later"),PageTemplate("later",[f2],onPage=later_page)])
    doc.build(st)
    return doc.page

# ---------------- run status: console + log + local dashboard ----------------
DASH_CSS="""*{box-sizing:border-box}body{margin:0;font:14px Arial,Helvetica,sans-serif;color:#222;background:#f4f5f9;height:100vh;display:flex;flex-direction:column}
header{background:#fff;border-bottom:1px solid #ddd;padding:12px 18px}h1{margin:0 0 8px;font-size:18px;color:#00539B}
.bar{height:14px;background:#e2e4f0;border-radius:7px;overflow:hidden}.bar div{height:100%;background:#00539B}
.stats{display:flex;gap:22px;margin-top:8px;flex-wrap:wrap}.stats b{color:#6B4C8A}
main{flex:1;display:flex;min-height:0}#list{width:380px;border-right:1px solid #ddd;background:#fff;display:flex;flex-direction:column}
#q{margin:10px;padding:7px 9px;border:1px solid #bbb;border-radius:4px}#rows{overflow:auto;flex:1}
.r{padding:8px 12px;border-bottom:1px solid #eee;cursor:pointer}.r:hover{background:#f0f2f7}.r.sel{background:#dde3f3}
.r small{color:#666;display:block}.r.fail{cursor:default;background:#fdeceb}.r.fail small{color:#a33}
.ok{color:#2a7a2a;font-weight:bold}.bad{color:#b33;font-weight:bold}
#pv{flex:1;display:flex;flex-direction:column}#pvbar{padding:8px 12px;background:#fff;border-bottom:1px solid #ddd;display:none;gap:12px;align-items:center}
#pvbar button{padding:4px 10px}#pvbar a{color:#00539B}iframe{flex:1;border:0;background:#888}#empty{margin:auto;color:#777}
#runbtn{display:none;margin-left:auto;padding:6px 14px;background:#00539B;color:#fff;border:0;border-radius:4px;cursor:pointer;font-weight:bold}#runbtn:disabled{background:#999;cursor:default}
#runmsg{color:#b33}"""
DASH_JS="""var running=%s,sel=decodeURIComponent(location.hash.slice(1));
function show(f,name){sel=f;location.hash=encodeURIComponent(f);
 document.querySelectorAll('.r').forEach(function(e){e.classList.toggle('sel',e.dataset.f===f)});
 document.getElementById('empty').style.display='none';var fr=document.getElementById('fr');fr.style.display='block';fr.src=f;
 var b=document.getElementById('pvbar');b.style.display='flex';document.getElementById('pvn').textContent=name;document.getElementById('pvo').href=f;}
function closePv(){sel='';history.replaceState(null,'',location.pathname);document.getElementById('fr').style.display='none';document.getElementById('fr').src='about:blank';
 document.getElementById('pvbar').style.display='none';document.getElementById('empty').style.display='block';
 document.querySelectorAll('.r').forEach(function(e){e.classList.remove('sel')});}
function filt(){var q=document.getElementById('q').value.toLowerCase();document.querySelectorAll('.r').forEach(function(e){e.style.display=e.textContent.toLowerCase().indexOf(q)>-1?'':'none'})}
document.querySelectorAll('.r[data-f]').forEach(function(e){e.onclick=function(){show(e.dataset.f,e.dataset.n)}});
if(sel){var e=document.querySelector('.r[data-f="'+CSS.escape(sel)+'"]');if(e)show(sel,e.dataset.n);}
setInterval(function(){if(running&&!sel)location.reload()},3000);
if(location.protocol.indexOf('http')===0){var rb=document.getElementById('runbtn');rb.style.display='inline-block';rb.disabled=running;
 rb.onclick=function(){rb.disabled=true;rb.textContent='Starting...';
  fetch('/run',{method:'POST',headers:{'X-SAH-Run':'1'}}).then(function(r){return r.text().then(function(t){if(!r.ok)throw new Error(t);setTimeout(function(){location.reload()},1000);})})
  .catch(function(err){rb.disabled=false;rb.textContent='Regenerate statements';document.getElementById('runmsg').textContent=err.message;});};}"""

def fmt_t(sec):
    sec=int(sec); return f"{sec//3600}h {sec%3600//60}m" if sec>=3600 else f"{sec//60}m {sec%60}s"

def write_dashboard(outdir,results,total,started,running):
    """Self-contained status page (no external fonts/scripts/links). Written to a temp file, then swapped in."""
    from html import escape as e
    done=sum(1 for r in results if r["ok"]); failed=len(results)-done; n=len(results)
    el=time.time()-started; eta=fmt_t(el/n*(total-n)) if n and running else "-"
    pct=100*n/total if total else 100
    state="Running" if running else f"Finished - {done} done, {failed} failed"
    rows=[]
    for r in reversed(results):
        lab=f'{e(r["name"])} <span style="color:#888">({e(r["id"])})</span>'
        if r["ok"]: rows.append(f'<div class="r" data-f="{e(r["file"])}" data-n="{e(r["name"])}">{lab}<small><span class="ok">Done</span> &middot; {r["pages"]} pages &middot; {e(r["period"])}</small></div>')
        else: rows.append(f'<div class="r fail">{lab}<small><span class="bad">Failed</span> &middot; {e(r["error"])}</small></div>')
    page=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Statement run - {e(state)}</title><style>{DASH_CSS}</style></head><body>
<header><h1>Support at Home statement run</h1><div class="bar"><div style="width:{pct:.1f}%"></div></div>
<div class="stats"><span><b>{e(state)}</b></span><span>Progress: <b>{n} of {total}</b></span><span>Done: <b>{done}</b></span><span>Failed: <b>{failed}</b></span>
<span>Elapsed: <b>{fmt_t(el)}</b></span><span>Time left: <b>{eta}</b></span><span>Updated: <b>{time.strftime('%H:%M:%S')}</b></span><span id="runmsg"></span><button id="runbtn">Regenerate statements</button></div></header>
<main><div id="list"><input id="q" placeholder="Search name or ID" oninput="filt()"><div id="rows">{''.join(rows)}</div></div>
<div id="pv"><div id="pvbar"><b id="pvn"></b><a id="pvo" target="_blank">Open PDF</a><button onclick="closePv()">Close preview</button></div>
<div id="empty">Select a finished statement to preview it.</div><iframe id="fr" style="display:none"></iframe></div></main>
<script>{DASH_JS % ('true' if running else 'false')}</script></body></html>"""
    tmp=os.path.join(outdir,".status.html.tmp")
    with open(tmp,"w",encoding="utf-8") as f: f.write(page)
    os.replace(tmp,os.path.join(outdir,"status.html"))

DATE_RE=re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})")
def iso_date(v):
    """DD-MM-YYYY (also D/M/YYYY, DD.MM.YY - as Excel saves Australian dates) or YYYY-MM-DD -> 'YYYY-MM-DD'.
    Raises ValueError if it isn't a real date."""
    v=v.strip(); m=DATE_RE.fullmatch(v)
    if m:
        dd,mm,yy=(int(x) for x in m.groups())
        return dt.date(yy+2000 if yy<100 else yy,mm,dd).isoformat()
    return dt.date.fromisoformat(v).isoformat()

REQUIRED=["client_id","title_name","period_start","period_end","quarter","month_in_quarter"]
def check_client(c,items=()):
    """Plain-English check of the fields every statement needs, before building.
    Dates in the client row and its line items are converted to YYYY-MM-DD in place."""
    missing=[k for k in REQUIRED if not (c.get(k) or "").strip()]
    if missing: raise ValueError("missing " + ", ".join(missing))
    for k in ("period_start","period_end","at_expiry","hm_expiry","rc_start","rc_end"):
        if (c.get(k) or "").strip():
            try: c[k]=iso_date(c[k])
            except ValueError: raise ValueError(f"{k} '{c[k]}' is not a date (use DD-MM-YYYY)")
    for r in items:
        if (r.get("date") or "").strip():
            try: r["date"]=iso_date(r["date"])
            except ValueError: raise ValueError(f"line item '{r.get('description','')}' date '{r['date']}' is not a date (use DD-MM-YYYY)")
    if c["month_in_quarter"].strip() not in ("1","2","3"): raise ValueError("month_in_quarter must be 1, 2 or 3")

TITLES={"mr","mrs","ms","miss","mx","dr","prof","sir","dame","rev","fr","sr"}
def pdf_name(c,stamp):
    """AC12345_Jane_Smith_2026-11_10-221530.pdf - client ID, first and last name (title dropped), run time."""
    words=re.sub(r'[<>:"/\\|?*\x00-\x1f]',"",c.get("title_name","")).split()
    if words and words[0].lower().rstrip(".") in TITLES: words=words[1:]
    safe_id=re.sub(r'[<>:"/\\|?*\x00-\x1f\s]',"",c["client_id"])
    return "_".join([safe_id]+words+[stamp])+".pdf"

CLIENT_COLS=REQUIRED+["addr1","addr2","addr3","country","provider_id","location","provider_phone","provider_hours","provider_email"]
ITEM_COLS=["client_id","section","status","date","category","description","rate","units","unit_cost","gov_subsidy","contribution"]
def validate_inputs(clients_csv,items_csv):
    """Check both CSVs before a run. Returns a list of plain-English problems (empty list = OK)."""
    problems=[]
    for label,path,cols in (("clients file",clients_csv,CLIENT_COLS),("line items file",items_csv,ITEM_COLS)):
        if not path: problems.append(f"Choose a {label}."); continue
        if not os.path.isfile(path): problems.append(f"The {label} can't be found: {path}"); continue
        try:
            with open(path,newline="",encoding="utf-8-sig") as f:
                rd=csv.reader(f); head=[h.strip() for h in next(rd,[])]
                has_rows=next(rd,None) is not None
        except PermissionError:
            problems.append(f"The {label} can't be opened - it may be open in Excel. Close it and try again: {path}"); continue
        except UnicodeDecodeError:
            problems.append(f"The {label} isn't saved as UTF-8. In Excel use Save As > 'CSV UTF-8 (Comma delimited)': {path}"); continue
        except (OSError,csv.Error) as ex:
            problems.append(f"The {label} can't be read as a CSV ({ex}): {path}"); continue
        if not head: problems.append(f"The {label} is empty: {path}"); continue
        missing=[c for c in cols if c not in head]
        if missing: problems.append(f"The {label} is missing these columns: {', '.join(missing)}. Check you picked the right file.")
        elif not has_rows and cols is CLIENT_COLS: problems.append(f"The {label} has no clients in it: {path}")
    return problems

def run(clients_csv,items_csv,outdir,on_progress=None,cancel_event=None):
    """Build one statement per client. Bad rows are skipped and logged, not fatal.
    on_progress(info) is called after each statement; setting cancel_event stops after the current one.
    Raises BrandingError for an unusable logo or provider.csv, OSError/KeyError for unreadable files (use validate_inputs first)."""
    load_logo(BRANDING); load_provider(BRANDING)
    os.makedirs(outdir,exist_ok=True); items=defaultdict(list)
    with open(items_csv,newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): items[r["client_id"]].append(r)
    with open(clients_csv,newline="",encoding="utf-8-sig") as f: clients=list(csv.DictReader(f))
    total=len(clients); results=[]; started=time.time(); done=failed=0; cancelled=False
    stamp=time.strftime("%Y-%m_%d-%H%M%S",time.localtime(started))   # same for every PDF in a run
    log_path=os.path.join(outdir,"errors.log")
    with open(log_path,"w",encoding="utf-8") as log:
        write_dashboard(outdir,results,total,started,True)
        for i,c in enumerate(clients,1):
            if cancel_event is not None and cancel_event.is_set(): cancelled=True; break
            cid=c.get("client_id","?"); name=c.get("title_name","?")
            info=dict(index=i,total=total,client_id=cid,name=name)
            try:
                check_client(c,items[cid]); fn=pdf_name(c,stamp)
                pages=build(c,items[cid],os.path.join(outdir,fn))
                results.append(dict(ok=True,id=cid,name=name,file=fn,pages=pages,period=c.get("period_start","")[:7]))
                done+=1; info.update(ok=True,pages=pages,file=fn)
            except Exception as ex:
                msg=f"{type(ex).__name__}: {ex}"
                results.append(dict(ok=False,id=cid,name=name,error=msg))
                log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {cid}  {name}  {msg}\n"); log.flush()
                failed+=1; info.update(ok=False,error=msg)
            write_dashboard(outdir,results,total,started,True)
            if on_progress: on_progress(dict(info,done_count=done,failed_count=failed,elapsed_seconds=time.time()-started))
        write_dashboard(outdir,results,total,started,False)
    if not failed and os.path.exists(log_path): os.remove(log_path)
    return dict(total=total,done=done,failed=failed,cancelled=cancelled,elapsed=time.time()-started,
                outdir=os.path.abspath(outdir),log=log_path if failed else None)

def main(clients_csv,items_csv,outdir):
    try: print(load_logo(BRANDING)); print(load_provider(BRANDING))
    except BrandingError as ex: sys.exit(str(ex))
    print(f"Dashboard: {os.path.abspath(os.path.join(outdir,'status.html'))}")
    def show(p):
        tail=f'{p["pages"]} pages, done' if p["ok"] else f'FAILED - {p["error"]}'
        print(f'Statement {p["index"]} of {p["total"]}: {p["name"]} ({p["client_id"]}), {tail}')
    try: s=run(clients_csv,items_csv,outdir,on_progress=show)
    except BrandingError as ex: sys.exit(str(ex))
    print(f"\nFinished: {s['done']} done, {s['failed']} failed, in {fmt_t(s['elapsed'])}.")
    if s["log"]: print(f"Failures logged to {s['log']}")

if __name__=="__main__":
    main(*(sys.argv[1:4] if len(sys.argv)>3 else ["clients.csv","line_items.csv","statements"]))
