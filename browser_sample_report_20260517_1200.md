# Browser sample validation report

Validation time: 2026-05-17 12:07:32 Asia/Shanghai

Method: Playwright opened each public YouTube `/about` page and extracted visible page text. Evidence below comes from browser-rendered text, not from `results.db`.

## Summary

- Sample size: 24
- PASS_BROWSER_EVIDENCE: 15
- NEEDS_PORTUGUESE_EVIDENCE: 1
- NEEDS_COUNTRY_EVIDENCE: 8

## By Bucket

- explicit_br_strict_pt: PASS_BROWSER_EVIDENCE=4
- explicit_br_lang_risk: PASS_BROWSER_EVIDENCE=3, NEEDS_PORTUGUESE_EVIDENCE=1
- null_country_br_signal: PASS_BROWSER_EVIDENCE=4, NEEDS_COUNTRY_EVIDENCE=2
- null_country_pt_only: NEEDS_COUNTRY_EVIDENCE=6, PASS_BROWSER_EVIDENCE=4

## Samples

### 1. Estrada de Chão (UC3roSgRik8z31LOkoTlBYIA)

- Bucket: `explicit_br_strict_pt`
- DB: subscribers=224000, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UC3roSgRik8z31LOkoTlBYIA/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 22.4万位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: brasil, sertanejo, com.br
- Browser PT hits: você, voce, seja, bem vindo, canal, aqui, conteúdo, conteudo, todos, muito, obrigado, aprenda
- Evidence lines:
  - Estrada de Chão
  - Canal sobre o Agronegócio e suas nuances.
  - metodoterrarica.com.br/vendas-mtr
  - Seja Bem vindo ao Estrada de Chão
  - FACEBOOK (curtir página) - https://www.facebook.com/pedrohenriqu...
  - Depoimento Sérgio

### 2. Emerok (UCRuFJfqcoLFSmxq1iXeWKHg)

- Bucket: `explicit_br_strict_pt`
- DB: subscribers=81700, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UCRuFJfqcoLFSmxq1iXeWKHg/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 8.17万位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: none
- Browser PT hits: você, voce, bem-vindo, canal, vídeo, video, aqui, conteúdo, conteudo, todos, dias, muita
- Evidence lines:
  - 🎮 Bem-vindo ao canal do Emerok! Aqui você aprende a subir de elo no Wild Rift com tier lists, guias de campeões, gameplay explicativa e bastidores dos campeonatos oficiais.
  - MUDOU MUITA COISA? OS CAMPEÕES MAIS FORTES DE CADA ROTA! TIERLIST DO PATCH 7.1 | LoL Wild Rift
  - ATÉ 20% DE DESCONTO
  - • VIRE MEMBRO DO CANAL E TENHA ACESSO DE VIDEOS EXCLUSIVOS:
  - • FICHA TÉCNICA
  - TALIYAH CHEGOU NO PATCH 7.1E! TESTANDO A NOVA CAMPEÃ NA JUNGLE | LoL Wild Rift

### 3. Projeto Caldo de Cana (UC9X7soxoyWDAvey9WcesUfg)

- Bucket: `explicit_br_strict_pt`
- DB: subscribers=24600, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UC9X7soxoyWDAvey9WcesUfg/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 2.46万位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: nordeste
- Browser PT hits: você, voce, canal, vídeo, video, aqui, conteúdo, conteudo, oficial, música, musica
- Evidence lines:
  - Caldo de Cana é um programa genuinamente cultural que tem como objetivo trazer música e vídeo de qualidade, sem limitações de estilo, gênero ou sucesso.
  - Usina Sonora - Músicas
  - Luiz Lins - Eu Tô Bem | Usina Sonora
  - Luiz Lins - A Música Mais Triste do Ano | Usina Sonora
  - Usina Sonora: Luiz Lins - Programa Na Íntegra
  - Márcio Oliveira | Batendo Papo no Usina Sonora

### 4. Ketlyn Geovana ♡ (UCFCSSS7nDiG3oDt9lIX_-9g)

- Bucket: `explicit_br_strict_pt`
- DB: subscribers=1400, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UCFCSSS7nDiG3oDt9lIX_-9g/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 1400位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: none
- Browser PT hits: você, voce, seja, bem vindo, canal, vídeo, video, aqui, todos, dias, muita
- Evidence lines:
  - bem vindos 💖
  - VLOG - DIAS DAS MÃES + COMPRINHAS 🛍
  - VLOG - TRABALHO + TREINOS/ ANIVERSÁRIO DELA 💖
  - #shortsfeed #shortvideo #shortsviral #shorts #processodeemagrecimento #emagrecimento
  - #shortsfeed #shortsviral #shortvideo #shorts
  - #shortsfeed #shortsviral #shortvideo #shorts #trend

### 5. ROMANCES DE ÉPOCA (UCWCqvXwHkjGnIAuVZM6Q8tA)

- Bucket: `explicit_br_lang_risk`
- DB: subscribers=92800, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UCWCqvXwHkjGnIAuVZM6Q8tA/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 9.28万位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: none
- Browser PT hits: canal, vídeo, video, aqui, todos
- Evidence lines:
  - ROMANCES DE ÉPOCA
  - ✨🏰 ROMANCES DE ÉPOCA – Donde el amor nunca pasa de moda. ❤️📖
  - EL BAILE QUE CAMBIÓ LA HISTORIA: La Venganza de ALVA VANDERBILT Contra la Reina de Nueva York
  - IA Restaura una Mansión Victoriana de 1860 ABANDONADA en Estados Unidos: ¡El Resultado es Increíble!
  - 🧼 LA ASQUEROSA REALIDAD: ¿Cómo era la HIGIENE en la ÉPOCA VICTORIANA?
  - 🩸 ¿Cómo era la NOCHE DE BODAS y la vida conyugal en la ERA VICTORIANA? 💍

### 6. Lohzao (UCFR3EJi8t57vUlNfEzNDpMw)

- Bucket: `explicit_br_lang_risk`
- DB: subscribers=31800, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UCFR3EJi8t57vUlNfEzNDpMw/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 3.18万位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: rio de janeiro
- Browser PT hits: vídeo, video
- Evidence lines:
  - Nesse vídeo eu consegui o novo pacote do Naruto no freefire
  - é emulador né? kkkkkk
  - Os cara Lançaram um FREE FIRE rio de janeiro na favela kkkkkkk
  - Atualização do Free Fire...

### 7. ana by arts (UC8EqV-grY9kQpZGQydt3ydA)

- Bucket: `explicit_br_lang_risk`
- DB: subscribers=47200, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UC8EqV-grY9kQpZGQydt3ydA/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 4.72万位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: none
- Browser PT hits: você, voce, muito, olá, ola, receitas
- Evidence lines:
  - SOBREMESA POUCO CALÓRICA E MUITO GOSTOSA
  - FAÇA ESSA MISTURA E TENHA UM LANCHE INCRIVEL
  - PÃO LOW CARB COM 3 INGREDIENTES
  - O MELHOR SALPICÃO PARA AS FESTAS DE FIM DE ANO!
  - PAVÊ DE OURO BRANCO | SOBREMESA perfeita pro seu ano novo
  - DALGONA COFFEE | Famoso café do tiktok

### 8. Banda Diesel (UC59enR3mGEs9ZDUKjgARCIA)

- Bucket: `explicit_br_lang_risk`
- DB: subscribers=1070, country=Brasil, target_reason=country=Brazil
- URL: https://www.youtube.com/channel/UC59enR3mGEs9ZDUKjgARCIA/about
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Browser visible subscribers: 1070位订阅者
- Browser visible country row Brazil: True
- Browser BR hits: brasil
- Browser PT hits: none
- Evidence lines:
  - Diesel - Belo Horizonte - Brasil

### 9. Kamila e Daniel (UC8NP2dKJ-G9dVuLbSqhBPEA)

- Bucket: `null_country_br_signal`
- DB: subscribers=33800, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UC8NP2dKJ-G9dVuLbSqhBPEA/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 3.38万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: brasil, mineiro, ceara, flamengo, cruzeiro, atletico mineiro, atlético mineiro
- Browser PT hits: você, voce, seja, sejam, bem-vindo, canal, inscreva, vídeo, video, olá, ola
- Evidence lines:
  - SEJAM BEM-VINDOS AO NOSSO CANAL! SE INSCREVA E SEJA UM MEMBRO DO CANAL
  - REACT ATLÉTICO MG 3 x 0 CRUZEIRO CRUZEIRENSE REVOLTADO COM A DERROTA
  - #react #galo #cruzeiro
  - React.  do Atlético Mineiro contra o Cruzeiro | Golaço de Zaracho na Arena MRV contra o Cruzeiro | Gol de Guilherme Arena contra o Cruzeiro na Arena MRV |  gol de Paulinho na Arena
  - Tem Maria on-line aí ??? #react #futebol #atleticomineiro #viral #shortvideo #gym
  - Tem Maria on-line aí ? #futebol #react #galo #viral #shortvideo #shorts

### 10. Marcos Orlandini  (UC-tvKLGE-Sl3_iOvxN27ZAA)

- Bucket: `null_country_br_signal`
- DB: subscribers=11000, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UC-tvKLGE-Sl3_iOvxN27ZAA/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 1.1万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: muita, olá, ola
- Evidence lines:
  - Olá, meu nome é Marcos Orlandini, sou especialista em soluções juridicas e investimentos imobiliários.
  - O que acham dessa chácara ? #santacatarina #natureza #viagem #sitioavenda
  - 6,5 Hectares em Águas Mornas! 🤯 (Preço INACREDITÁVEL)
  - O que acham desse tipo de imóvel ? #santacatarina #sitio #natureza
  - CHÁCARA EM ÁGUAS MORNAS  - SANTA CATARINA  #santacatarina #natureza #vidanocampo #sitio
  - SÍTIO INCRÍVEL EM RANCHO QUEIMADO - SC | MUITA PASTAGEM | RICO EM ÁGUA | 4.8 HECTARES

### 11. Beatriz Andrade (UC9Jd-MpuIr4vlunpFESYPLg)

- Bucket: `null_country_br_signal`
- DB: subscribers=23400, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UC9Jd-MpuIr4vlunpFESYPLg/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 2.34万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: com.br
- Browser PT hits: você, voce, canal, vídeo, video, aqui, todos, olá, ola
- Evidence lines:
  - Canal sobre maquiagem, cabelo afro/crespo/cacheado, Faça você mesmo/Diy e outras coisas do universo feminino.
  - jeitinhoproprio.blogspot.com.br
  - Micropigmentação de Sobrancelha Fio a Fio - Pele Negra
  - Todos os vídeos do canal sobre cuidados com o cabelo
  - Penteado + Faça você mesmo (hendband) - Cabelo crespo/cacheado
  - Cabelo Crespo/Cacheado: Parei de usar química! E agora??? #1 Transição

### 12. Corre Brasilis (UCsTamDvCt4j2v5mrlzqYS7Q)

- Bucket: `null_country_br_signal`
- DB: subscribers=2420, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCsTamDvCt4j2v5mrlzqYS7Q/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 2420位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: brasil, brasileir
- Browser PT hits: você, voce, canal, inscreva, inscreva-se, vídeo, video, aqui
- Evidence lines:
  - Corre Brasilis
  - @CorreBrasilis
  - Corre Brasilis é o seu canal de vídeos curtos, flagras e memes do cotidiano brasileiro! 🇧🇷
  - O argentino não aguentou o pré-Carnaval 🔥🎭
  - Toda família tem esse Natal 🧑‍🎄
  - Depois de um dia puxado, só isso aqui salva ❤️

### 13. Léo Medeiros (UCNalsCNNx84Q6j_mutQ_8AQ)

- Bucket: `null_country_br_signal`
- DB: subscribers=10600000, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCNalsCNNx84Q6j_mutQ_8AQ/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 1060万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: você, voce, vídeo, video, aqui, todos, dias, muito, muita
- Evidence lines:
  - Léo Medeiros
  - Vídeos todos os dias às 17h!⏰
  - 24 HORAS NO PÂNTANO DOS JACARÉS *fomos atacados
  - 24 HORAS A DERIVA NO PÂNTANO DOS JACARÉS *sobrevivi?
  - GATO MIA NO SÍTIO DO LÉO *nível extremo
  - TUDO QUE ACHAMOS NO LIXO *muita coisa boa

### 14. Rod Postal (UCjc35jjWhVDtw3SirKN_WhA)

- Bucket: `null_country_br_signal`
- DB: subscribers=40700, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCjc35jjWhVDtw3SirKN_WhA/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 4.07万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: com.br
- Browser PT hits: aqui
- Evidence lines:
  - Maquiador e influencer!
  - LÁPIS E MÁSCARA VERDE! 💚 #maquiagem #vizzela #vizzela #mascara
  - BLUSH VERMELHO! 🔥 #maquiagem #blush #beleza
  - BLUSH EM CREME VS EM PÓ 🔥 #maquiagem #blush #tutorial
  - GLOSS BT GLAZE DE BRUNA TAVARES! #maquiagem #brunatavares #resenha #gloss
  - PERFUME MANCHA??? 🤔 #maquiagem #makeup #perfume #kabeauty

### 15. REGINALDO PORTILHO (UCS9a_eBLqdYiA_3mJWXc6dw)

- Bucket: `null_country_pt_only`
- DB: subscribers=15200, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCS9a_eBLqdYiA_3mJWXc6dw/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 1.52万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: você, voce, canal, vídeo, video, aqui
- Evidence lines:
  - Sou apaixonado por Volkswagens e por aqui compartilho essa paixão!
  - 😱 QUE RARIDADE! Você COMPRARIA esse GOL GTI? | Golzinho quadrado | Project car
  - Encontramos um gol GTI raro cheio de formigas! Será que vamos comprar?
  - 😨 BATEU FORTE!  Saveiro Super Surf G3 vai precisar de peças novas! Project car
  - Aplicamos EPÓXI na SAVEIRO QUADRADA 1997
  - HÁ 10 ANOS ABANDONADO | Project car de um Gol quadrado CHT 1995

### 16. WM Vintage Club (UCNkZI3MN6F6fezJ1wmeVBVA)

- Bucket: `null_country_pt_only`
- DB: subscribers=19900, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCNkZI3MN6F6fezJ1wmeVBVA/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 1.99万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: você, voce, canal, inscreva, aqui, olá, ola, música, musica
- Evidence lines:
  - Canal do salão mais incrível de Sorocaba. Aqui você vai encontrar tudo sobre nossos eventos, playlists das músicas que rolam enquanto você manda aquele corte, e dicas incríveis dos

### 17. Gaby Azevedo- Trader (UCkAS8ZwCY34DY5hXTwAOyhw)

- Bucket: `null_country_pt_only`
- DB: subscribers=1240, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCkAS8ZwCY34DY5hXTwAOyhw/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 1240位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: seja, bem vindo, canal, todos, olá, ola
- Evidence lines:
  - Esse canal tem a finalidade de explanar ideias, estrategias, observações e analises gráficas do mercado financeiro, especialmente de day trade em mini-indice e mini-dolar.
  - The dove landed on my heart - A pomba pousou em meu coração
  - Venda no mini dólar- 75 reais operando pelo celular- #daytrade  #trader
  - Operando pelo celular- trader B3- 54 reais no índice                              @eugabycabralv
  - Seja todos bem vindos!

### 18. Joyce Lopes (UCJmh73kPiGhN2xzvUsbNCBg)

- Bucket: `null_country_pt_only`
- DB: subscribers=88200, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCJmh73kPiGhN2xzvUsbNCBg/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 8.82万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: você, voce, dias
- Evidence lines:
  - As definições de gateira foram atualizadas
  - DIY: CAMA ECOLÓGICA FÁCIL
  - A QUANTIDADE IDEAL DE ÁGUA PARA O SEU GATO
  - COMO ESCOLHER A RAÇÃO DO SEU GATO
  - AGORA VAI? TEMOS NOVIDADES: NOVOS VOLUNTÁRIOS!
  - O que você acha de quem abandona seu animal?

### 19. D F s (UCNbWIdXQ5Nt87rt0pDT4iHQ)

- Bucket: `null_country_pt_only`
- DB: subscribers=6410, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCNbWIdXQ5Nt87rt0pDT4iHQ/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 6410位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: brazil, rio de janeiro
- Browser PT hits: vídeo, video
- Evidence lines:
  - Os Melhores videos da interwebs. 🎥📲
  - Abertura Opening - FORMATION LIVE MIAMI BEYONCÉ
  - Fogos Copacabana Reveillon 2016 Rio de Janeiro Brazil
  - Ring The Alarm Beyoncé Ambulance BeyHive FAN VERSION

### 20. Victor Hugo | Vendas  (UCoNE6jXS4DZS060WJY9s96w)

- Bucket: `null_country_pt_only`
- DB: subscribers=2110, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCoNE6jXS4DZS060WJY9s96w/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 2110位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: vendas
- Evidence lines:
  - Victor Hugo | Vendas
  - 🚦Te ensino sobre empreendedorismo e vendas na rua de forma realista 👇🏻
  - Me segue ✅ #vendas #empreendedor
  - ME SEGUE ✅ #vendas #empreendedor
  - Rotina de um Vendedor de Rua #vendas
  - Use a rua como ponte para seu objetivo ✅ #vendas

### 21. canal falido (UCONubdfhAL1WPL-7dE4-_Cw)

- Bucket: `null_country_pt_only`
- DB: subscribers=8860, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCONubdfhAL1WPL-7dE4-_Cw/about
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Browser visible subscribers: 8860位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: none
- Browser PT hits: você, voce, canal
- Evidence lines:
  - canal falido
  - @canalfalido555
  - ✨️ranking de melhores momentos de séries e filmes 🎬
  - RANKING MOMENTOS ENGRAÇADOS DO PETER GRIFFIN
  - RANKING MOMENTOS ENGRAÇADOS DE FAMILY GUY
  - Ranking momentos engraçados do Peter Griffin kkkkk

### 22. Educação Físicaa (UCQHZF9XqePvTPLTzDh-OltA)

- Bucket: `null_country_pt_only`
- DB: subscribers=12100, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCQHZF9XqePvTPLTzDh-OltA/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 1.21万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: com.br
- Browser PT hits: você, voce, vídeo, video, olá, ola, aprenda, educação, física
- Evidence lines:
  - Educação Físicaa
  - @EducacaoFisicaa
  - Videos sobre assuntos da Educação Física.
  - twitter.com/educacaofisicaa
  - Ideia para sua aula De Educação Física
  - Bebê tentar livrar a bola da cesta

### 23. Bebeto Kamayura (UCTY2ITOT0Om-TH1UczZ0-Qg)

- Bucket: `null_country_pt_only`
- DB: subscribers=137000, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCTY2ITOT0Om-TH1UczZ0-Qg/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 13.7万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: kamayura
- Browser PT hits: seja, canal, vídeo, video, olá, ola, dança
- Evidence lines:
  - Bebeto Kamayura
  - @BebetoKamayura
  - Indígena do Xingu-MT da etnia kamayura,Língua tupi
  - Cerimônia kwarup está chegando
  - Churrascaria tradicional do povo originário
  - Flautistas e as dançarinas só alegria 🤩

### 24. Engenharia da Dança (UCCfDcHKFBnWcCdUMAbj2nCQ)

- Bucket: `null_country_pt_only`
- DB: subscribers=14000, country=None, target_reason=country=None,lang=pt
- URL: https://www.youtube.com/channel/UCCfDcHKFBnWcCdUMAbj2nCQ/about
- Browser verdict: `PASS_BROWSER_EVIDENCE`
- Browser visible subscribers: 1.4万位订阅者
- Browser visible country row Brazil: False
- Browser BR hits: com.br
- Browser PT hits: dança, engenharia
- Evidence lines:
  - Engenharia da Dança
  - @engenhariadadanca
  - Com a intenção de continuar crescendo, se atualizando e sempre com um diferencial, atualmente estão sendo realizados cursos de ballet clássico, jazz, patinação artística, sapateado
  - engenhariadadanca.com.br
  - Engenharia da Dança - Natal Espetacular
  - Engenharia da Dança - Mamma Mia
