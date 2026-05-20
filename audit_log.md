# Audit Log

## Round 1 — 2026-05-16 23:20 CST

DB state: 3472 total rows, 2298 targets (all subs >= 1000).

Sampled 10 random eligible channels.

| channel_id | name | DB subs | live subs | DB country | live country | target_reason | verdict |
|---|---|---:|---:|---|---|---|---|
| UCZcSWDert8saxIttTP-CJTg | Franquia do Brasil | 233000 | 233000 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCx4dzaHskbnHDozu6A4i0Ww | Raissa 23 | 59300 | 59300 | Brasil | Brasil | country=Brazil | PASS |
| UCm6hH-k25uLNqK7f-edOoKg | Som Automotivo Um Sonho | 3350 | 3350 | Brasil | Brasil | country=Brazil | PASS |
| UCWq24CQsQS3xNb8F-I3Miog | Hiroshi Satoi | 20300 | 20300 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCNrthyyJVjrJUpePrl6lW_g | Neagle | 19200000 | 19200000 | Brasil | Brasil | country=Brazil | PASS |
| UCFyNAPz9HEJJTU2GNa21bHQ | Profa Anelize | 96000 | 96000 | Brasil | Brasil | country=Brazil | PASS |
| UC9NXpIA01HVRhYgcEbs80Nw | Sony Pictures Brasil | 1050000 | 1050000 | Brasil | Brasil | country=Brazil | PASS |
| UCN-opsqqDunWO6h5uCp9Y4g | Hoje em Dia | 3540000 | 3540000 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCboQVvqJnosNG-gGGt_SH6g | As melhores da midia... | 3300 | 3300 | Brasil | Brasil | country=Brazil | PASS |
| UC-C7ceAp4OXixgsOJVEfxqg | DJ Ramonstro | 2490 | 2490 | Brasil | Brasil | country=Brazil | PASS |

Round 1 results: **10/10 pass** (100% true-positive rate). Sub counts matched exactly; all NULL-country channels truly Portuguese.

## Round 2 — 2026-05-16 23:52 CST

DB state at sample time: 19363 total rows. Sampled 15 random eligible channels (subs >= 1000, is_target=1).

| channel_id | name | DB subs | live subs | DB country | live country | target_reason | verdict |
|---|---|---:|---:|---|---|---|---|
| UCYqaJF_qFtPSKZ-pLeIt2_g | Michel Lima | 1220 | 1220 | Brasil | Brasil | country=Brazil | PASS |
| UCn67qAYbMyhqbrh75sQuFgg | Edson Lima - Oficial | 231000 | 231000 | Brasil | Brasil | country=Brazil | PASS |
| UC9Erg7Bn8rtCAuZd4ZCdU5A | ZATALA | 13500 | 13500 | Brasil | Brasil | country=Brazil | PASS |
| UC0MEj7rp256_82tmzHWV8UQ | Papo Cidades | 49300 | 49300 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCdyRsrpnAu5paLU9fwp3cTg | A Bola do jogo | 7290 | 7290 | Brasil | Brasil | country=Brazil | PASS |
| UCptA63YJ4KqyeUZN065SzTg | SKULL KNIGHT | 2440 | 2440 | Brasil | Brasil | country=Brazil | PASS |
| UCCJC7YIZytEccbU0AWQIBHA | Falaidearo | 12100000 | 12100000 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UClX5XxKybuYgf1Q-0jAy8Sw | Cortes da Paula Ferreira [OFICIAL] | 32900 | 32900 | Brasil | Brasil | country=Brazil | PASS |
| UCbQO-W1VPj6CEaf-ByHxddw | Só Fla | 16900 | 16900 | Brasil | Brasil | country=Brazil | PASS |
| UCSiszAJ2KUvjGea3imhKJpw | Copart Brasil | 44000 | 44000 | Brasil | Brasil | country=Brazil | PASS |
| UCl7Mc3cYsFbnN4Z_GE09pAA | Como Que? | 5190 | 5190 | Brasil | Brasil | country=Brazil | PASS |
| UCO-ZtzKY8aU493oyZPwYTJg | Dr. Eudes Tarallo | 48400 | 48400 | Brasil | Brasil | country=Brazil | PASS |
| UC_XaPuIU8n8rM5z44iygzEw | TerritorioTupiniquim | 115000 | 115000 | Brasil | Brasil | country=Brazil | PASS |
| UCF43CwdxJNt7UsnOxnMh8qg | Matilha Equilibrada | 45500 | 45500 | Brasil | Brasil | country=Brazil | PASS |
| UCIahKJr2Q50Sprk5ztPGnVg | Canal dotNET | 43100 | 43100 | Brasil | Brasil | country=Brazil | PASS |

Round 2 results: **15/15 pass** (100% true-positive rate). Sub counts matched exactly; both NULL-country channels confirmed Portuguese by langdetect on live descriptions. Note: 2 of 15 needed a single SSL retry because the production scraper saturates connections.

## Round 3 — 2026-05-17 00:36 CST

DB state at sample time: 20219 total rows. Note: the production process was suspended (SIGSTOP, STAT=TN) shortly after Round 2; only ~210 new rows arrived in 40 min. We waited the user-specified ~35 min interval and proceeded with a fresh random sample of 15 channels from the existing data.

| channel_id | name | DB subs | live subs | DB country | live country | target_reason | verdict |
|---|---|---:|---:|---|---|---|---|
| UCvOHHWVKwPd_oCH73I1ukKQ | Grupo Doze por Oito | 67300 | 67400 | Brasil | Brasil | country=Brazil | PASS (+0.1%) |
| UCVebeMk4o7RafIi__QlR_sQ | Gustavo Conti Guitarra & Tecnologia | 7050 | 7060 | Brasil | Brasil | country=Brazil | PASS (+0.1%) |
| UCA3f-GJ7_tOKDCTc-0XaQHw | Camilla Santana | 589000 | 589000 | Brasil | Brasil | country=Brazil | PASS |
| UCgghxRgG77xWe7hiJAe40NQ | tuka ps | 67900 | 67900 | Brasil | Brasil | country=Brazil | PASS |
| UCzrJp8MIHnfDcYBzl4IKwqw | Victor Degasperi | 149000 | 149000 | Brasil | Brasil | country=Brazil | PASS |
| UC01Cet33obQ_IW2Qand1t6A | Pequeno Genio | 1740000 | 1740000 | Brasil | Brasil | country=Brazil | PASS |
| UCapMwstGCQ7gGCoppfBDX-w | canal PRETO E BRANCO CSC | 8730 | 8730 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCNL8Z2LQzKZ-AASoKe9zxnA | Claudia Oliveira Receitas | 197000 | 197000 | Brasil | Brasil | country=Brazil | PASS |
| UCBdTTKcV3q8RSKJcWaKDAwg | Plique Games | 350000 | 350000 | Brasil | Brasil | country=Brazil | PASS |
| UCRcSy6ZudIN1EJhWE62eXdg | Descendo a porrada | 26500 | 26500 | Brasil | Brasil | country=Brazil | PASS |
| UCyTCpuEtLjhnzfNjnPcEz8w | CRIANÇAS KIDS | 268000 | 268000 | Brasil | Brasil | country=Brazil | PASS |
| UCF2Ufe3dzuOz3Ct-jas0txA | Dr. André Nascimento \| Contra Abusos Bancários | 2670 | 2670 | Brasil | Brasil | country=Brazil | PASS |
| UCuQjD2JLU7vy9OdSVFwRR5g | Essencialismo | 9080 | 9080 | Brasil | Brasil | country=Brazil | PASS |
| UCqw_71HInCmv4zQViWt33Ug | Violão sem Drama - Roberta Feroli | 54300 | 54300 | Brasil | Brasil | country=Brazil | PASS |
| UCAsjyL8hky0uXJOnaOM0ktg | Juarez Receitas Caseiras | 356000 | 356000 | Brasil | Brasil | country=Brazil | PASS |

Round 3 results: **15/15 pass** (100% true-positive rate). All sub counts within 0.2%; NULL-country channel confirmed Portuguese.

## Round 4 — 2026-05-17 01:14 CST

DB state at sample time: 20219 total rows (production scraper remained suspended in STAT=TN throughout the round-3-to-4 interval). Sampled 15 fresh random channels.

| channel_id | name | DB subs | live subs | DB country | live country | target_reason | verdict |
|---|---|---:|---:|---|---|---|---|
| UCwSE3LmfzUsVzhWHVGE9Bog | Anderson E Vei da Pisadinha Oficial | 644000 | 644000 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCR06tOt_Gn6J032D66v_8YQ | COROA VIDA LOKA OFICIAL | 416000 | 416000 | Brasil | Brasil | country=Brazil | PASS |
| UCg7Fr4VR9GnuopvhrE-6FwA | Nossa Onda \| Por Mirella e Zinho | 77600 | 77600 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UCt8g7YBkNa6ftoP9qXcBHVw | Adriana Taissun | 3610 | 3610 | Brasil | Brasil | country=Brazil | PASS |
| UCAJAbdjUtxGM9zaD_epYpcA | CANAL SUPREN | 100000 | 100000 | Brasil | Brasil | country=Brazil | PASS |
| UCXsNBWCCcNUNMKAxqt-zCNQ | Manu Pedrini | 264000 | 264000 | Brasil | Brasil | country=Brazil | PASS |
| UC2kTz3-DrCbsN6dcNuac3aQ | Ana Gomes | 137000 | 137000 | Brasil | Brasil | country=Brazil | PASS |
| UC8ErCFkZL7NcEQqcXERJnqQ | Rodrigo PortoBike | 1500 | 1500 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |
| UC7N415OcSE3weR9t9VWCGWg | Empresária das ruas Tânia Vieira | 67600 | 67600 | Brasil | Brasil | country=Brazil | PASS |
| UCku2y_NLzbWoJpvX2PRrRdg | Geo Colombo Beauty | 5270 | 5280 | Brasil | Brasil | country=Brazil | PASS (+0.2%) |
| UCqYR6j-1IEbiOY4n3Q64RbQ | Sesc no Pará | 3790 | 3800 | Brasil | Brasil | country=Brazil | PASS (+0.3%) |
| UCx2tsANnhacjiqisNmPnl-Q | Spok | 5620000 | 5620000 | Brasil | Brasil | country=Brazil | PASS |
| UCYj1jy66peKPzEp808TK5ww | Raiam Santos McArn | 1130000 | 1130000 | Brasil | Brasil | country=Brazil | PASS |
| UCSyiZ3JohfPVi-G8gB3qjCA | Kilometragem ® | 46500 | 46500 | Brasil | Brasil | country=Brazil | PASS |
| UCvmtT51uZ7vxOHWstlyhm5Q | Lipen | 149000 | 149000 | NULL | None | country=None,lang=pt | PASS (langdetect=pt) |

Round 4 results: **15/15 pass** (100% true-positive rate). All sub counts within 0.3%; all 4 NULL-country channels confirmed Portuguese by langdetect on live descriptions.
