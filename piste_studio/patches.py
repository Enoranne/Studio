from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from .locks import check_operation
from .versioning import create_patch_version

def create_validated_patch(root:Path,*,edit_name:str,base_version:str,operation:str,start:float|None,end:float|None,target:str,property_name:str|None,old_value:str|None,new_value:str|None,explicit_soft_unlock:bool=False):
    decision=check_operation(root,operation=operation,start=start,end=end,target=target,explicit_soft_unlock=explicit_soft_unlock)
    if not decision.allowed: raise ValueError(f"PATCH refusé : {decision.decision} — {decision.reason}")
    patch={"schema_version":1,"created_at":datetime.now(timezone.utc).isoformat(),"base_version":base_version,"scope":{"operation":operation,"target":target,"start":start,"end":end,"property":property_name},"change":{"old":old_value,"new":new_value},"lock_validation":{"decision":decision.decision,"reason":decision.reason,"explicit_soft_unlock":explicit_soft_unlock},"execution":{"status":"PENDING_TESSERACT","note":"V0.02 enregistre et valide le patch mais ne l'exécute pas encore."}}
    return create_patch_version(root,edit_name,base_version,patch)
