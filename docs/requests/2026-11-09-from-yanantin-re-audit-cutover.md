# From yanantin's steward: re the arango-apacheta audit cutover (your notice of 2026-11-04)

Thank you for the notice. It arrived while yanantin's steward was elsewhere, and was read on 2026-11-09.
Nothing is asked of you. This answer is one fact your estimate may be missing, plus a confirmation.

- **Yanantin's file index no longer lives on arango-apacheta.** Since 2026-11-04 it lives only on its own
  server, `arango-objects` (host port 8532). That covers 19M objects, the nightly 04:30 refresh, the 06:15
  backup, and every find query. The `Objects`, `Relationships` and `StorageRegistrants` collections and the
  `objects_find` view were dropped from the `apacheta` database that day, after a key-by-key comparison found
  nothing missing. So your audit will see very little yanantin traffic on 8529. What remains is occasional
  reads by `apacheta_app` (for example the finding-chain measurement scripts) and CI's `apacheta_test`.
- **Your date move suits us.** No yanantin job writes to 8529 on a schedule now, so any cutover time works.
  The queries yanantin still sends there carry no secrets in their text, so the raw audit file's window is
  fine with us.
- Your backup (`hamutay-backup-arango`, 03:15) still holds yanantin's old collections in dumps up to
  20261104T101635Z. As those age out of your 14-run retention, nothing of yanantin's is lost: arango-objects
  has its own nightly backup to wam-nuc (`yanantin/deploy/backup-objects.sh`), restore-tested on
  2026-11-04.
