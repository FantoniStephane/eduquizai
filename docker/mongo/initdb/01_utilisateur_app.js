// Compte applicatif MongoDB d'EduQuizAI (principe du moindre privilège).
//
// L'application ne se connecte jamais avec le compte root : elle utilise ce
// compte, limité à sa propre base (et à la base des tests automatisés).
// - readWrite : lire, créer, modifier et supprimer les quiz ;
// - dbAdmin   : règle de validation ($jsonSchema) et index (commande init_mongo),
//               suppression de la base de test en fin de tests.
// Aucun droit sur les autres bases ni sur l'administration du serveur.
//
// Exécuté automatiquement par l'image mongo au premier démarrage (volume vide).
// Sur une base existante, se relance sans risque (création ou mise à jour).

const nomBase = process.env.MONGO_DB;
const utilisateur = process.env.MONGO_APP_USER;
const motDePasse = process.env.MONGO_APP_PASSWORD;

if (!nomBase || !utilisateur || !motDePasse) {
  throw new Error(
    "MONGO_DB, MONGO_APP_USER et MONGO_APP_PASSWORD doivent être définis."
  );
}

const roles = [
  { role: "readWrite", db: nomBase },
  { role: "dbAdmin", db: nomBase },
  { role: "readWrite", db: `test_${nomBase}` },
  { role: "dbAdmin", db: `test_${nomBase}` },
];

const base = db.getSiblingDB(nomBase);
if (base.getUser(utilisateur)) {
  base.updateUser(utilisateur, { pwd: motDePasse, roles: roles });
  print(`Compte « ${utilisateur} » mis à jour.`);
} else {
  base.createUser({ user: utilisateur, pwd: motDePasse, roles: roles });
  print(`Compte « ${utilisateur} » créé.`);
}
