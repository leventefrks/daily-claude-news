module.exports = `Az alábbi hírcímek a mai Telex és 444.hu oldalakról származnak.
Válaszd ki a 8 legfontosabb hírt, és mindegyikhez írj egy rövid, 1-2 mondatos magyar nyelvű összefoglalót.
Minden összefoglalót kizárólag magyarul írj!
Visszaadandó formátum – szigorúan JSON lista, semmi más:

[
  {"index": <eredeti_index>, "summary": "<1-2 mondatos magyar összefoglaló>"},
  ...
]

Cikkek:
{articles}
`;
