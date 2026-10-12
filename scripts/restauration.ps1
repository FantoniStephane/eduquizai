<#
.SYNOPSIS
    Restaure les bases d'EduQuizAI à partir d'une sauvegarde de sauvegarde.ps1.

.DESCRIPTION
    ATTENTION : les données actuelles sont REMPLACÉES par celles de la
    sauvegarde (tables PostgreSQL et collection des quiz MongoDB).
    Une confirmation est demandée avant de commencer, sauf avec -Oui.

    Le conteneur web est arrêté pendant la restauration (aucune écriture
    pendant l'opération), puis relancé.
    - PostgreSQL : pg_restore --clean en une seule transaction : en cas
      d'erreur, la base reste dans son état d'origine.
    - MongoDB : mongorestore --drop, limité à la base de l'application, avec
      le compte applicatif (la règle de validation et les index sont restaurés).

.PARAMETER Dossier
    Dossier de la sauvegarde, par exemple sauvegardes\2026-10-11_13-40-00.

.PARAMETER Oui
    Ne pas demander de confirmation.

.EXAMPLE
    .\scripts\restauration.ps1 sauvegardes\2026-10-11_13-40-00
#>

param(
    [Parameter(Mandatory = $true)] [string]$Dossier,
    [switch]$Oui
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Etape {
    <# Lance une commande externe et s'arrête si elle échoue. #>
    param([string]$Libelle, [scriptblock]$Commande)
    Write-Host "- $Libelle"
    & $Commande
    if ($LASTEXITCODE -ne 0) { throw "Échec : $Libelle (code $LASTEXITCODE)." }
}

$dumpPostgres = Join-Path $Dossier "postgres.dump"
$archiveMongo = Join-Path $Dossier "mongo.archive.gz"
foreach ($fichier in @($dumpPostgres, $archiveMongo)) {
    if (-not (Test-Path $fichier)) { throw "Fichier introuvable : $fichier" }
}

if (-not $Oui) {
    Write-Host "Les données actuelles vont être remplacées par la sauvegarde $Dossier." -ForegroundColor Yellow
    $reponse = Read-Host "Tapez OUI pour continuer"
    if ($reponse -cne "OUI") { Write-Host "Restauration annulée."; exit 1 }
}

Invoke-Etape "Arrêt du conteneur web" { docker compose stop web }
try {
    Invoke-Etape "PostgreSQL : copie du fichier" {
        docker compose cp $dumpPostgres postgres:/tmp/eduquizai.dump
    }
    Invoke-Etape "PostgreSQL : pg_restore" {
        docker compose exec -T postgres sh -c 'pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists --no-owner --single-transaction /tmp/eduquizai.dump'
    }
    Invoke-Etape "PostgreSQL : nettoyage du conteneur" {
        docker compose exec -T postgres rm /tmp/eduquizai.dump
    }

    Invoke-Etape "MongoDB : copie du fichier" {
        docker compose cp $archiveMongo mongo:/tmp/eduquizai.archive
    }
    Invoke-Etape "MongoDB : mongorestore" {
        docker compose exec -T mongo sh -c 'mongorestore --quiet --username $MONGO_APP_USER --password $MONGO_APP_PASSWORD --authenticationDatabase $MONGO_DB --nsInclude=$MONGO_DB.\* --drop --archive=/tmp/eduquizai.archive --gzip'
    }
    Invoke-Etape "MongoDB : nettoyage du conteneur" {
        docker compose exec -T mongo rm /tmp/eduquizai.archive
    }
}
finally {
    Invoke-Etape "Redémarrage du conteneur web" { docker compose start web }
}

Write-Host "Restauration terminée depuis $Dossier" -ForegroundColor Green
