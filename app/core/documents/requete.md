
## Caractérisation du besoin

### Signature de documents

On souhaite pouvoir faire signer des documents par les utilisateurs de l'application. 
Chaque groupe de permission doit pouvoir demander la signature aux utilisateurs qu'il veut, suivre les documents (signés, en attente, rejetés...), les templates disponibles.

## Implémentation technique proposée

### Utilisation de Documenso

La solution se base sur Documenso qui est déjà en place dans l'écosystème MyECL. 
Il suffit à chaque équipe voulant utiliser l'intégration de nous fournir une clé API qui nous permettra de générer les documents à leur place. Cette équipe sera liée à un groupe MyECL pour savoir quelles personnes ont les droits sur quels documents. 


### Introduction des documents

La signature des documents se fait via Documenso et ses templates, on cherchera à exploiter au maximum le webhook de documenso pour gérer la plupart des taches (création/modification/suppression de templates, signature/rejet de documents). Le modules doit tout de même prévoir un certain nombre d'accès API pour pouvoir afficher les informations en tant qu'utilisateur ou effectuer des actions en tant qu'admin. Le module sera principalement utilisé à travers un site en NextJS + React pour l'interface. Étant donné le grand volume de documents a envoyer sur de faibles périodes, nous n'utiliserons pas la fonctionnalité d'envoi de mail de Documenso mais plutot un embedding React avec le signing_token des documents générés (document.recipients[0].token).

**Ajout de tables en BDD :**
- document_team:
    - team_id: UUID
    - group_id: str
    - name: str
    - api_key: str
- document_template: 
    - id: UUID
    - documenso_id: str
    - name: str
    - team_id: str
    - deleted: bool
    - document_directory_id: str | None = None
- document_document:
    - id: UUID
    - template_id: UUID (ForeignKey)
    - module: str
    - user_id: str (ForeignKey)
    - signing_token: str
    - status: DocumentStatus

**Principe :**
Lors de la création d'un template par une équipe, le webhook est appelé par Documenso et MyECL enregistre son existence et ses données, le document_directory_id (dossier d'arrivée des documents généré à partir du template) est initialisé à None et peut être modifié par le groupe propriétaire depuis l'interface MyECL.
On utilise l'interface pour générer un document en signature pour chaque utilisateurs d'une liste.
Chaque utilisateur peut se rendre sur le site et accéder à la liste des documents signés, à signé, rejetés...
L'utilisateur peut demander à récupérer le signing token d'un document qui lui ait destiné (aucune autre personne ne doit pouvoir accéder à ce token).
Après signature ou rejet, Documenso appelle le WebHook qui note la réponse.

**Enpoints et logique**
- GET, POST, PATCH, DELETE pour les teams
- GET, PATCH (document_directory_id uniquement)
- GET, POST pour les documents (ou PATCH /use sur les templates à la place du POST)
- Un WebHook qui traite : TEMPLATE_CREATED, TEMPLATE_UPDATED, TEMPLATE_DELETED, DOCUMENT_COMPLETED, DOCUMENT_REJECTED