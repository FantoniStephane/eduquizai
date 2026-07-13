CREATE TABLE utilisateur(
   Id_utilisateur COUNTER,
   nom VARCHAR(50) NOT NULL,
   prenom VARCHAR(50) NOT NULL,
   email VARCHAR(100) NOT NULL,
   mot_de_passe VARCHAR(255) NOT NULL,
   PRIMARY KEY(Id_utilisateur),
   UNIQUE(email)
);

CREATE TABLE lecon(
   Id_lecon COUNTER,
   titre VARCHAR(100) NOT NULL,
   contenu TEXT NOT NULL,
   Id_utilisateur INT NOT NULL,
   PRIMARY KEY(Id_lecon),
   FOREIGN KEY(Id_utilisateur) REFERENCES utilisateur(Id_utilisateur)
);

CREATE TABLE quizz(
   Id_quizz COUNTER,
   titre VARCHAR(100) NOT NULL,
   description TEXT,
   date_de_creation DATE NOT NULL,
   Id_lecon INT NOT NULL,
   PRIMARY KEY(Id_quizz),
   FOREIGN KEY(Id_lecon) REFERENCES lecon(Id_lecon)
);

CREATE TABLE question(
   Id_question COUNTER,
   texte TEXT NOT NULL,
   type_question VARCHAR(20) NOT NULL,
   Id_quizz INT NOT NULL,
   PRIMARY KEY(Id_question),
   FOREIGN KEY(Id_quizz) REFERENCES quizz(Id_quizz)
);

CREATE TABLE reponse(
   Id_reponse COUNTER,
   texte TEXT NOT NULL,
   est_correcte LOGICAL NOT NULL,
   Id_question INT NOT NULL,
   PRIMARY KEY(Id_reponse),
   FOREIGN KEY(Id_question) REFERENCES question(Id_question)
);
