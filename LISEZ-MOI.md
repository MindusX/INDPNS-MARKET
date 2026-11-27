# Profil INDPNS Market — géré exactement comme Mindus Forge

## Ce qui est repris de Mindus Forge
| Mindus Forge                              | INDPNS Market (ce zip)                                   |
|-------------------------------------------|----------------------------------------------------------|
| Images stockées EN BASE (BYTEA)           | Table accounts_profileimage (BinaryField)                |
| URL versionnée ?v=<horodatage>            | /api/profile/avatar/<id>?v=…  et  /api/profile/cover/<id>?v=… |
| ETag + cache immuable                     | idem (304 sans recharger l'image)                        |
| POST /api/profile/upload-avatar | -cover  | idem (multipart, champ « file »)                         |
| DELETE /api/profile/avatar | cover        | idem                                                     |
| PUT /api/profile/cover/position           | idem (cadrage vertical 0–100 %)                          |
| Recadrage photo (zoom, glisser, pincement)| idem, modale « Recadrer votre photo »                    |
| Aperçu immédiat puis URL serveur          | idem (aperçu local, puis URL versionnée)                 |
| Repositionnement de la couverture         | idem (glisser-déposer + Enregistrer)                     |
| Synchronisation entre onglets             | BroadcastChannel                                         |
| JPEG progressif q88, avatar 800 px, cover 2400 px, alpha aplati, EXIF supprimé | idem |

## Différence volontaire (confidentialité)
Mindus est un réseau social : photos visibles par tous. Ici, l'image n'est servie que si le profil est PUBLIC,
ou au propriétaire / à l'équipe (staff). Sinon 404 et l'interface affiche l'initiale.

## Installation
Copier le zip sur le projet (mêmes chemins) et redéployer. Rien d'autre :
sync_schema (déjà installé) crée au démarrage la table accounts_profileimage et les 3 colonnes ajoutées à accounts_user.
Les anciennes photos (enregistrées sur le disque éphémère) sont perdues : à téléverser à nouveau.
Tests : python manage.py test tests.test_profiles
Admin > Utilisateurs > action « Supprimer les photos de profil et de couverture (modération) ».
