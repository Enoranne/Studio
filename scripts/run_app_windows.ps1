param([Parameter(Mandatory=$true)][string]$Project)
python -m piste_studio.app --project $Project
