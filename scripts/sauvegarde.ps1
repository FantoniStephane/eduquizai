<#
.SYNOPSIS
    Sauvegarde les deux bases d'EduQuizAI : PostgreSQL (comptes, leçons) et
    MongoDB (quiz).

.DESCRIPTION
    Les sauvegardes sont faites dans les conteneurs (pg_dump, mongodump), puis
    copiées dans sauvegardes\<date_heure>\ :
      - postgres.dump     : format personnalisé de pg_dump (compressé) ;
      - mongo.archive.gz  : archive compressée de mongodump.
    MongoDB est sauvegardée avec le compte applicatif (droits limités à la base
    de l'application), pas avec le compte root.

    Le dossier sauvegardes\ est ignoré par Git : il contient des données
    personnelles (comptes des enseignants) et ne doit jamais être publié.

.EXAMPLE
    .\scripts\sauvegarde.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Etape {
    <# Lance une commande externe et s'arrête si elle échoue. #>
    param([string]$Libelle, [scriptblock]$Commande)
    Write-Host "- $Libelle"
    & $Commande
    if ($LASTEXITCODE -ne 0) { throw "Échec : $Libelle (code $LASTEXITCODE)." }
}

$horodatage = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$dossier = Join-Path "sauvegardes" $horodatage
New-Item -ItemType Directory -Force -Path $dossier | Out-Null
Write-Host "Sauvegarde dans $dossier"

# PostgreSQL : le fichier est créé dans le conteneur puis copié (une redirection
# PowerShell pourrait abîmer un fichier binaire).
Invoke-Etape "PostgreSQL : pg_dump" {
    docker compose exec -T postgres sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f /tmp/eduquizai.dump'
}
Invoke-Etape "PostgreSQL : copie du fichier" {
    docker compose cp postgres:/tmp/eduquizai.dump "$dossier/postgres.dump"
}
Invoke-Etape "PostgreSQL : nettoyage du conteneur" {
    docker compose exec -T postgres rm /tmp/eduquizai.dump
}

# MongoDB : base de l'application uniquement, avec le compte applicatif.
Invoke-Etape "MongoDB : mongodump" {
    docker compose exec -T mongo sh -c 'mongodump --quiet --username $MONGO_APP_USER --password $MONGO_APP_PASSWORD --authenticationDatabase $MONGO_DB --db $MONGO_DB --archive=/tmp/eduquizai.archive --gzip'
}
Invoke-Etape "MongoDB : copie du fichier" {
    docker compose cp mongo:/tmp/eduquizai.archive "$dossier/mongo.archive.gz"
}
Invoke-Etape "MongoDB : nettoyage du conteneur" {
    docker compose exec -T mongo rm /tmp/eduquizai.archive
}

Get-ChildItem $dossier | Format-Table Name, Length -AutoSize
Write-Host "Sauvegarde terminée : $dossier" -ForegroundColor Green
