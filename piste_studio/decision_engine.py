from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json

from .config import read_yaml
from .metadata import fetch_media_with_metadata

ELIGIBLE_STATUSES={"APPROVED","CANONICAL","SAFETY"}

def _stable_hash(obj:dict)->str:
    payload=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")); return sha256(payload.encode("utf-8")).hexdigest()

def _score_media(item:dict)->tuple:
    return (int(bool(item.get("canonical"))),1 if item.get("status")=="CANONICAL" else 0,int(item.get("rating") or 0),1 if item.get("status")=="SAFETY" else 0,-int(item.get("spoiler_level") or 0),-int(item.get("id") or 0))

def _eligible_media(root:Path,max_spoiler:int)->list[dict]:
    candidates=[]
    for item in fetch_media_with_metadata(root):
        if item["kind"] not in {"video","image"} or item["status"] not in ELIGIBLE_STATUSES or not bool(item["trailer_safe"]) or int(item["spoiler_level"])>max_spoiler: continue
        candidates.append(item)
    candidates.sort(key=_score_media,reverse=True); return candidates

def _beat_template(duration_seconds:float)->list[dict]:
    ratios=[("hook",.12,"Créer une accroche sensorielle immédiate."),("discovery",.22,"Présenter l'objet, le geste ou le monde sans exposition lourde."),("play",.26,"Donner du rythme et de la matière : jeu, voix, sons, interactions."),("emotion",.22,"Faire apparaître la dimension émotionnelle sans révélation majeure."),("ending",.18,"Retomber vers le motif sonore final et le carton titre.")]
    cursor=0.; beats=[]
    for i,(name,ratio,purpose) in enumerate(ratios):
        end=float(duration_seconds) if i==len(ratios)-1 else round(cursor+duration_seconds*ratio,3); beats.append({"name":name,"start":round(cursor,3),"end":end,"duration":round(end-cursor,3),"purpose":purpose}); cursor=end
    return beats

def build_teaser_brief(root:Path,*,duration_seconds:float,mood:list[str]|None=None,max_spoiler:int=0,aspect_ratio:str|None=None)->tuple[dict,dict]:
    if duration_seconds<=0: raise ValueError("duration_seconds doit être > 0.")
    if not 0<=max_spoiler<=3: raise ValueError("max_spoiler doit être compris entre 0 et 3.")
    canon=read_yaml(root/"canon.yaml"); locks_doc=read_yaml(root/"locks.yaml"); candidates=_eligible_media(root,max_spoiler); beats=_beat_template(duration_seconds)
    for idx,beat in enumerate(beats):
        if candidates:
            c=candidates[idx%len(candidates)]; beat["primary_media_id"]=c["id"]; beat["primary_media_path"]=c["relative_path"]; beat["primary_media_reason"]="Sélection déterministe selon canon, statut, rating, trailer-safe et spoiler."
        else: beat["primary_media_id"]=None; beat["primary_media_path"]=None; beat["primary_media_reason"]="Aucun média admissible catalogué."
    pool=[{"id":c["id"],"path":c["relative_path"],"status":c["status"],"spoiler_level":c["spoiler_level"],"canonical":bool(c["canonical"]),"rating":int(c.get("rating") or 0),"title":c.get("title"),"description":c.get("description"),"duration_seconds":c.get("duration_seconds"),"tags":c.get("tags",[])} for c in candidates]
    locks=[{"name":l.get("name"),"start":l.get("start"),"end":l.get("end"),"level":l.get("level"),"forbidden":l.get("forbidden",[])} for l in locks_doc.get("locks",[])]
    brief={"schema_version":2,"deliverable":{"type":"teaser","duration_seconds":float(duration_seconds),"aspect_ratio":aspect_ratio or canon.get("visual",{}).get("aspect_ratio","16:9"),"mood":mood or ["mysterious","emotional"],"max_spoiler_level":max_spoiler},"canon":canon,"locks":locks,"selection_policy":{"eligible_statuses":sorted(ELIGIBLE_STATUSES),"trailer_safe_required":True,"max_spoiler_level":max_spoiler,"prefer_canonical":True,"prefer_higher_rating":True},"candidate_pool":pool,"suggested_beats":beats,"editorial_instructions":["Le brief n'autorise aucune modification du master.","Les HARD LOCKS doivent être considérés comme non modifiables.","Préserver les silences, respirations et motifs sonores du canon.","Éviter tout effet ou transition explicitement exclu par le canon.","Ce plan de beats est une proposition : le futur moteur de montage doit rendre chaque choix traçable."]}
    decisions={"schema_version":1,"engine":"piste-studio-decision-engine","candidate_count":len(pool),"candidate_ids":[c["id"] for c in pool],"canon_sha256":_stable_hash(canon),"locks_sha256":_stable_hash(locks_doc),"brief_sha256":_stable_hash(brief),"notes":["Aucune coupe réelle n'est exécutée en V0.02.","Les affectations de médias aux beats sont déterministes et révisables."]}
    return brief,decisions
