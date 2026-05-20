# Browser random-1000 validation report

Validation time: 2026-05-17 15:15:12 Asia/Shanghai

Method: 1000 rows were randomly sampled from the SQLite snapshot, then each public YouTube `/about` page was opened in a Playwright browser session. The verdict uses browser-rendered text, not only DB fields.

## Summary

- Sample size: 1000
- PASS_BROWSER_EVIDENCE: 968
- NEEDS_COUNTRY_EVIDENCE: 27
- NEEDS_PORTUGUESE_EVIDENCE: 5

## By DB Country

- country_BR: PASS_BROWSER_EVIDENCE=849, NEEDS_PORTUGUESE_EVIDENCE=5
- country_NULL: PASS_BROWSER_EVIDENCE=119, NEEDS_COUNTRY_EVIDENCE=27

## Non-Pass Samples

### 55. Papo Fora do Script, com Josias Junior (UCT6CMkA6gRt47CqCSumK22A)

- DB: subscribers=5790, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 5860位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, bem-vindo, canal, vídeo, video, aqui, conteúdo, conteudo, muita, dança, família, familia, história, historia
- Evidence lines:
  - Bem-vindo ao PAPO FORA DO SCRIPT, com Josias Junior.
  - Por Que Estou Aqui no YouTube?
  - Muita gente perguntando: "...por onde você anda?"; "...por que esse canal?"
  - Pois é... Neste vídeo, eu esclareço o motivo! É só assistir...
  - #josiasjunior #icm #igrejacristamaranata #meupodcast #historiasdevida #históriasdefamília #inspiração  #superação
  - AMADEU LOUREIRO, uma história de vida!
  - Experiências, Mudanças e Propósito! A história de uma família que cruzou o planeta.
  - Quem foi GEDELTI GUEIROS? O que ninguém sabe sobre esse servo de Deus e grande líder.

### 104. BRISA7 FF (UCR5B6B3W3G7FFntU1cng3fw)

- DB: subscribers=27100, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2.71万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, vídeo, video, vídeos, videos, todos, muito, obrigado
- Evidence lines:
  - Jogador focado no competitivo de Free Fire 🏆 A meta é chegar na FFWS 🙏🏅
  - ULTIMA FINAL DO ANO - LDS LEAGUE - FOMOS CAMPEÕES!? 🏆👀 HIGHLIGHTS EM CAMPEONATOS! S24 ULTRA
  - OBRIGADO 2025! 🎉❤️ QUE VENHA 2026! 🔥HIGHLIGHTS EM CAMPEONATOS! S24 ULTRA
  - FINAL DA STRIKE LEAGUE - FOMOS CAMPEÕES!? 🏆🔥 HIGHLIGHTS EM CAMPEONATOS! S24 ULTRA
  - AMASSANDO NO ALTO NÍVEL DO FF! ☠️👺HIGHLIGHTS EM CAMPEONATOS! S24 ULTRA
  - Amanhã as 10hrs no canal, vídeo da rodada 9 da LAFF‼️🚨Não percam, um dos melhores vídeos do canal!!!!
  - Amanha as 10hrs no canal! Final presencial regional do torneio estudantil de Free Fire! 🔥👀
  - Bora que nós não pode parar, amanhã as 10hrs tem mais um vídeo BRABO no canal, final da speed league que fomos campeões! não percam que tá incrível 🚨🔥

### 149. SNOWTER (UC6xQfp2yLMKZtYwxm63aojg)

- DB: subscribers=56000, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 5.6万位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 163. Sabedoria da Alma (UCWcrnCgJ4R6Fz4pvkTVqzNQ)

- DB: subscribers=41100, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 4.11万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, canal, vídeo, video, aqui
- Evidence lines:
  - No Sabedoria da Alma, você encontrará reflexões profundas sobre a mente, a alma e o universo invisível que habita dentro de você. Este canal compartilha palestras que despertam a consciência, exploram o poder do inconsci
  - SE VOCÊ SE SENTE PERDIDO E VAZIO, ESTE VÍDEO VAI TE AJUDAR - Carl Jung Psicologia
  - O MOMENTO EM QUE VOCÊ SE ESCOLHE MUDA TODO O SEU DESTINO - Carl Jung Psicologia
  - COMO DEIXAR IR ALGUÉM QUE AINDA MORA EM VOCÊ - Carl Jung Psicologia
  - 10 CHAVES PARA CORTAR O VÍNCULO EMOCIONAL SEM DOR - Carl Jung Psicologia
  - Este espaço é para quem sente que a vida vai além do óbvio. Para aqueles que perceberam padrões que se repetem, emoções que não compreendem, comportamentos que não conseguem explicar com lógica. Aqui, falamos sobre arqué
  - Os temas abordados neste canal tocam o essencial: o inconsciente coletivo, o desenvolvimento da consciência, a dualidade do ser, o equilíbrio entre luz e sombra, o significado dos símbolos no cotidiano e como trabalhar c

### 242. Especialista Utilitário  (UCUNXDfAT9vpYLk55diJ9ffg)

- DB: subscribers=284000, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 28.4万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, aqui, dicas
- Evidence lines:
  - Especialista Utilitário
  - COMPRINHAS QUE VALERAM CADA CENTAVO VERSÃO COZINHA #achadinhos #shopee #dicas
  - PORCARIAS DA INTERNET QUE EU TESTEI E HOJE NÃO VIVO MAIS SEM #achadinhos #shopee #dicas
  - ACHADOS DA SHOPEE QUE ME ARREPENDI DE TER COMPRADO SÓ AGORA #achadinhos #shopee #dicas
  - ACHADOS DA SHOPEE PARA ACABAR COM CAOS EM CASA QUE VOCÊ PRECISA CONHECER #achadinhos #shopee #dicas
  - TEM NA CASA DE RICA MILIONÁRIA, MAS EU ACHEI TUDO NA SHOPEE #achadinhos #shopee #dicas
  - ACHADOS DA SHOPEE QUE ENGANAM QUALQUER VISITA #achadinhos #shopee #dicas
  - TER UMA TELA DE CINEMA EM CASA É MAIS BARATO QUE TELEVISÃO ( PROJETOR R15A )

### 250. Ludmila Laiane (UCyGiNqFAmN1du-80k6J8lvw)

- DB: subscribers=10600, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.06万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vídeo, video, vídeos, videos, conteúdo, conteudo, olá, ola, dicas
- Evidence lines:
  - Olá meninas, eu sou a Lud, vamos postar vários vídeos de dicas e tutoriais pra vcs, cuidados diários com o cabelo, penteados entre outros 😍.
  - Tutorial! Fazendo Babyliss no meu Cabelo, faça você mesma. #tutorial #façavocêmesmo
  - Passo a Passo para fazer Banho de Brilho com Coloração em casa/ faça você mesma
  - Dicas de cuidados com o cabelo loiro, loiro perfeito.
  - Inspiração de Cor do Cabelo da Virgínia/ Cor e Corte renovado #virginia #cores #loira #corte
  - Uma produção maravilhosa ✨
  - Qual tipo de conteúdo gostam mais?

### 282. Mr Cortes (UCX-dtsLAuXKO4U_KlyHhq3w)

- DB: subscribers=2710, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 2710位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 300. ClickHouse (UCODADD6kbJcv807t962udLQ)

- DB: subscribers=1290, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1290位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: none
- Evidence lines:
  - Empresa fabricante de casas modulares com método construtivo próprio, de grande rapidez de construção e altas prestações térmica e acústica.
  - Feng Shui ClickHouse | Conceito Feng Shui | Construção Modular
  - ClickHouse | O nosso método construtivo | Casas Modulares | Modular Architecture
  - ClickHouse | Conceito Neo | A constução de uma habitação modular desde o início
  - Apresentação ClickHouse Algarve | Casa Modelo Fuseta | Construção Modular
  - ClickHouse | Arquitetura Modular | As fases de uma construção modular

### 377. Receitas Fáceis (UC388yvGzvXqDt7jfq3ov7uw)

- DB: subscribers=4240, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 4240位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: olá, ola, receitas
- Evidence lines:
  - Receitas Fáceis
  - @receitasfaceis4243
  - Receitas Fáceis para o dia a dia 😀
  - Jiló frito crocante 😋
  - Molho de alho para churrasco super prático 😋😋😋
  - Enroladinho de salsicha 😋
  - Bolo de fubá de liquidificador rápido
  - www.youtube.com/@receitasfaceis4243

### 474. Rafaela de Sá Beauty (UCHI7jWKV9JNGHwlMwqJ0izw)

- DB: subscribers=2470, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2470位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, sejam, bem-vindo, aprenda, dicas
- Evidence lines:
  - Rafaela de Sá Beauty
  - Rotina, estética e propósito! 🤍
  - Deus faz tudo acontecer na HORA CERTA | essa mensagem vai se confirmar no seu coração
  - Lista básica de materiais | DESIGN DE SOBRANCELHAS
  - Uma mensagem do meu coração | Deus quer falar com você
  - Você nunca mais vai aplicar HENNA da mesma maneira | COMO APLICAR A HENNA
  - COMO DEPILAR O BUÇO | Cera, fio ou pinça
  - DESIGNER DE SOBRANCELHAS EM 2026 | Meu curso online - APRENDA DO ZERO

### 485. Bya Artes em Bijuterias  (UCn2nzIuDDgOcLQEckcvRFTg)

- DB: subscribers=40300, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 4.04万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, canal, inscreva, inscreva-se, vídeo, video, vídeos, videos, aqui, muito, olá, ola, aprenda, dicas
- Evidence lines:
  - Transforme pérolas e miçangas em verdadeiras joias com tutoriais simples e criativos!
  - alguns modelos de colares disponíveis no meu curso de bijuterias para iniciantes.
  - “Aprenda bijuterias mesmo sendo iniciante”
  - 🌸 A pulseira mais delicada que você vai ver hoje! ✨
  - 🌼 Pulseira de Pérolas Fácil de Fazer | Aprenda no Meu Curso de Bijuterias
  - “TODO MUNDO me pergunta como faço essa pulseira de pérolas 😍✨”
  - “Aprenda essa pulseira floral PERFEITA para vender muito 💜”.
  - Essa técnica simples deixa a pulseira com cara de joia!

### 493. RBHard Gamer (UCjV3ZxGRb5jyJevQewXhPwg)

- DB: subscribers=3530, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3530位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, seja, sejam, bem-vindo, canal, inscreva, inscreva-se, vídeo, video, vídeos, videos, conteúdo, conteudo
- Evidence lines:
  - Sejam bem-vindos ao canal RBHard Gamer, um canal que traz vários temas sobre jogos!
  - Se Inscreva-se e deixa o like que foi dificil de gravar esse vídeo, vem o resumo sobre o Poppy Playtime.  Poppy Playtime é um jogo eletrônico de terror e Sobrevivência e quebra-cabeça lógico desenvolvido e publicado pela
  - Poppy Playtime Chapter 5 - Jogo Completo Sem Comentários| Dublado e legendado
  - Hello Neighbor 2 - Jogo Completo Sem Comentários
  - Silent Hill 2  -  Jogo Completo Sem Comentários - Legenda PT/BR
  - Poppy Playtime Chapter 4 - Jogo completo Dublado - Sem comentários
  - Poppy Playtime Chapter 1 - Jogo Completo Sem Comentário
  - Poppy Playtime Chapter 2 - Jogo completo Sem Comentários

### 553. TheTruPlayers (UC521vgi-Kq7Lsh-zTziEbqg)

- DB: subscribers=3020, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3020位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, inscreva, inscreva-se, vídeo, video, todos, história, historia
- Evidence lines:
  - Dois jovens aprendendo a viver nesse mundo virtual ! Comentários, unboxings, gameplays e tudo mais sobre games!
  - Unboxing Resident Evil Village Edição Padrão PS4
  - Unboxing do Resident Evil 8, um dos jogos mais esperados de 2021, na sua versão para PS4.
  - Avalie o vídeo e inscreva-se no canal se ainda não é inscrito!
  - Espero que todos estejam bem e se cuidando em casa da melhor maneira possível.
  - Tudo de bom à todos vocês s2
  - Unboxing Doom Eternal Edição Padrão PS4
  - Unboxing The Last of Us Part 2 Edição Padrão PS4

### 571. Luana Ferreira gomes (UCIwCP2YioXPDaFBGbk0JnHQ)

- DB: subscribers=38200, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3.82万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: vídeo, video, vídeos, videos
- Evidence lines:
  - Vlog rotina da manhã 🤎✨️📸✅️
  - #shortvideo #gravidez #fyp
  - #vlog #shortvideo #explore
  - #gravidez #shortvideo #viral
  - Descobrindo minha segunda gravidez 💖🩵#gravity #viral #shortvideo
  - #viral #minivlog #shortvideo #explore
  - Rotina morando no interior da Espanha 🇪🇸#viral #vlog #shortvideo
  - videos✅️

### 577. sheyla lanna (UCo4wdAdhIh6FGRBegRoq0sA)

- DB: subscribers=2220, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2220位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, canal, inscreva, inscreva-se, aqui, olá, ola, dicas, história, historia
- Evidence lines:
  - 🎉 Olá, sou a Sheyla Lanna e minha missão é te ensinar a trabalhar com buffet infantil e buffet de casamento!
  - Como empreender na cozinha | Minha história real
  - Como Começar um Buffet Sem Experiência
  - Como Fazer Festa para 50 Pessoas na Prática
  - Bolo de chocolate com morango
  - Aqui você vai aprender como precificar corretamente cada serviço e obter lucro de forma inteligente.
  - 💡 Com dicas práticas e estratégias comprovadas, você poderá se destacar em cada festa e atender cada cliente com excelência.
  - 🚀 Inscreva-se no canal e ative o sininho para não perder nenhuma dica e dominar tudo sobre buffets!

### 601. Mau&Ju (UCBX6ZcgBF7WJis66iU3czhA)

- DB: subscribers=2710, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2710位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, aqui, dicas
- Evidence lines:
  - Aqui nós vamos compartilhar com vocês um pouco da nossa vida nos EUA e trazer as melhores ideias de passeios e restaurantes.
  - PREÇOS DOS TÊNIS NO OUTLET MAIS BARATO DE ORLANO
  - Quantas atrações dá pra fazer em 1 dia na Universal? Fizemos dois parques!
  - POR ISSO QUE ESSA É A MELHOR ÉPOCA PRA VIR AQUI! (Flower & Garden 2026)
  - Fizemos um passeio na Universal que quase ninguém conhece (Portofino Bay)
  - Dicas para aproveitar o Disney Magic Kingdom - melhores atrações, onde comer, fura-fila e mais!
  - Não vá para a Disney sem comprar isso no Walmart
  - Preços da Black Friday 2025 nos Estados Unidos!

### 606. YUCCA PLANTAS OFICIAL (UCHftyadDxp1IyQkMN6tCZfw)

- DB: subscribers=4780, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 4780位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, bem-vindo, canal, inscreva, inscreva-se, aqui, oficial, muito, muita, olá, ola, aprenda, dicas
- Evidence lines:
  - YUCCA PLANTAS OFICIAL
  - @YUCCAOFICIAL
  - Bem-vindo ao Yucca Plantas Oficial, um canal criado para quem ama a natureza, cultiva com carinho suas plantinhas ou quer começar no maravilhoso mundo da jardinagem! Aqui você encontra dicas simples e práticas sobre cult
  - COMIGO NINGUÉM PODE - Folhagem gigante!!
  - Conheça a FLOR PARAQUEDAS!! Ceropegia sandersonii
  - Conheça duas plantas LINDAS E RARAS do gênero Callisia!
  - Conheça a linda FLOR DO DRAGÃO - Huernia keniensis
  - Aprenda como cultivar a AVELOZ!

### 614. Alex Quintanilha ins @alexqnt25 (UCNo0JBNM-58PgrDZpwPGzsg)

- DB: subscribers=13500, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.35万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: canal
- Evidence lines:
  - SIGA O CANAL TROPA @alexqnt25 no Instagram
  - SÓ RELÍQUIA 🚂❤️🤴🥇
  - Nós não tinha nada..💭 @Oruam Siga nossa página no Instagram @alexqnt25
  - Tz da Coronel com a minha tropa é NO LOVE ! 🧞‍♂️💎
  - Mc Rodson sensação de poder 💪🏽🫡 siga nosso Instagram tropa @alexqnt25
  - Show do Chefin part 2 criançada invade o palco 👶👑🚀
  - Madrugadas reais meu inimigo é só eu, isso não é nada demais pra quem tem um sonho, tu tem que entender sinais nesse mundo estranho ! #tzdacoronel
  - CHEFIN FEAT WAZE LANÇAMENTO 🚀 SEGUE NOSSO CANAL TROPA SÓ INSTAGRAM ig alexqnt25

### 644. JDS edits (UCsXIDcmikKMLOdy9qT8oGaw)

- DB: subscribers=1340, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1350位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, canal, música, musica
- Evidence lines:
  - Canal somente com intenção de divulgar boas músicas com clipes de minha criação e também divulgando algumas músicas de criação própria (Grupo Som e Magia),espero que gostem.
  - Zé Neto e Cristiano-Pai de Menina (Clipe)
  - Grupo Som e Magia- A Lareira (Clipe) -versão em Português BR  kamin - EMIN & JONY
  - Grupo Som e Magia-Canção Para Você
  - Grupo Som e Magia-Tempo de Recomeçar
  - Grupo Som e Magia-Declaração de Amor
  - Grupo Som e Magia-Esse Coração
  - Grupo Som e Magia-Amo Você,Mas Aprendi A Me Amar Mais

### 645. Banda Diesel (UC59enR3mGEs9ZDUKjgARCIA)

- DB: subscribers=1070, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 1070位订阅者
- Visible country row Brazil: True
- BR hits: brasil, belo horizonte
- PT hits: none
- Evidence lines:
  - Diesel - Belo Horizonte - Brasil
  - Diesel (Banda) ao Vivo | Show completo em Belo Horizonte
  - 巴西

### 660. cheffmarly (UCgr7GvMiOTexOm5AHo2sAjg)

- DB: subscribers=43500, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 4.35万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: canal, vídeo, video, vídeos, videos, aqui, dicas
- Evidence lines:
  - Canal novo da Chef Marly Mazza o canal antigo com quase 50 mil inscritos foi haqueado e agora estamos com um perfil novo por aqui, então bora se inscrever e dar aquela força comentando e compartilhando os vídeos ❤️🙏
  - Bolo de fubá com goiabada fácil de fazer da Chef Marly #bolodefuba #bolo #bolocaseiro #dicas
  - Bolinho de polvilho frito fácil de e não vai estourar #bolinhofrito #receita #dicas #food
  - Massa integral para pães, pizza e salgados assados #pãocaseiro #sfiha #salgadosassados #receita
  - Como fazer um pré fermento com batata salsa para um pão caseiro fofinho
  - Pão integral caseiro mais fofinho e fácil de fazer do YouTube
  - Pão caseiro fácil de fazer e sem segredos🥖 #pão  #pãocaseiro #receita #youtube
  - Pão de mel de travessa fit fácil de fazer e fica uma delícia 😋 #paodemel #fitness #dicas #receita

### 709. WA Alimentos (UC4J2JrDn8D6OHj-Gy8_WR8w)

- DB: subscribers=3820, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3820位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: canal, vídeo, video, conteúdo, conteudo, dicas
- Evidence lines:
  - Dicas no nosso canal do YouTube sobre cortes e temperos!
  - FILÉ DO PEIXE DE PIRARARA... VÍDEO DETALHADO ESTAR NO CONTEÚDO DO MEU CANAL.

### 730. ANIMAL LEGENDS (UCujjjVhNKwi32EJLHqk_0xg)

- DB: subscribers=39300, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 3.93万位订阅者
- Visible country row Brazil: True
- BR hits: sus
- PT hits: none
- Evidence lines:
  - 巴西

### 765. MarinaMarvet  (UCp4pZZuJaIPKr8mW7yyHgQQ)

- DB: subscribers=7710, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 7720位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: aqui, aprenda, brinquedos
- Evidence lines:
  - Aprenda aqui como faço algumas das minhas artes, animais de biscuit, miniaturas e customizações!!
  - Customizei o cavalinho igual o embaixador do pepê.
  - Fiz uma miniatura diferente, uma nova raça de cavalo.
  - Vida equina, sua novelinha de cavalos em miniatura. #cavalo #novelinha #brinquedos #cavalominiatura
  - Customizei o cavalo our generation #brinquedos #cavalo #cavalodebrinquedo #ourgeneration
  - Fiz o touro bandido em biscuit #brinquedos #horse #tourobandido #rodeio
  - Customizei um cavalinho em homenagem ao embaixador do Pepê! #brinquedos #cavalo #cavalodebrinquedo

### 822. Victor Molin - Produzindo Conteúdo com seu iPhone! (UCcnh6s19XPF4dypShGWyfxA)

- DB: subscribers=25500, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2.55万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, bem-vindo, canal, vídeo, video, aqui, conteúdo, conteudo, todos, muito, aprenda, futebol, dicas, história
- Evidence lines:
  - Victor Molin - Produzindo Conteúdo com seu iPhone!
  - Aprenda a Fotografar e Filmar Melhor Com Seu iPhoen!
  - Bobby Moore: A História Por Trás Dessa Foto Lendária
  - O Homem em Queda: A História da Foto Que Parou o Mundo
  - Pelé, o sombrero e a foto que eternizou o Rei do Futebol no topo do mundo
  - Essa é umas das fotos mais reproduzidas do mundo!
  - A foto símbolo da Grande Depressão foi alterada para parecer ainda mais impactante.
  - Configurações IDEAIS do iPhone 14, Pro e Pro Max (iOS 26) 📱

### 827. EletrocarReck Dia A Dia Da Oficina (UC5NajJulpNiNqGL7ErI7yYA)

- DB: subscribers=6500, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 6500位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, canal, muito, olá, ola, obrigado, humor
- Evidence lines:
  - Em nosso canal mostraremos o Dia A Dia de uma auto elétrica,a parte bonita,boa e também as dificuldades do dia-a-dia.Nossos atendimentos externos, além de mostrar como nesse mundo existem pessoas boas...
  - Três corola no Mesmo Dia! Coincidência?
  - A oficina está Lotada! Muitos Desafios nesse dia!
  - Eco Sport Não Funciona Com Motor Quente (Resolvido)
  - Auto Elétrica Passando conhecimentos Pra Você
  - Sábadoouu!Picolé se Apresentando!kkkk
  - Sobrou até para o mecânico 👨🏻‍🔧 #humor #mecanico #mecanica #oficina
  - A Oficina Virou Zoológico Cada Dia Um Bicho Apronta Uma #viralshort #eletrocar #mecanica

### 852. SOU ESTRATEGISTA (UCwtlUWslUU9Lcr0dJsKeXBg)

- DB: subscribers=1690, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1690位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, canal, vídeo, video, vídeos, videos, aqui, conteúdo, conteudo, todos, muito, olá, ola, vendas
- Evidence lines:
  - A gente vive o que ensina — e aqui te mostramos como você também pode viver com mais intenção, organização e liberdade.
  - O ERRO QUE DESTRÓI O SEU FIM DE SEMANA (Desligue a chave) 🛑🚗
  - POR QUE VOCÊ NÃO CONSEGUE RELAXAR NA SEXTA-FEIRA 🛑🧠
  - HÁBITO TÓXICO QUE ACABA COM A SUA ROTINA (E como parar) 🛑🐒
  - POR QUE A SUA ORGANIZAÇÃO É UMA MENTIRA 🛑🗑️
  - VERDADEIRO MOTIVO DO SEU CANSAÇO (Pare de fazer isso) 🛑🧠
  - O HÁBITO INVISÍVEL QUE ZERA SUA ENERGIA (Pare com isso) 🛑🪫
  - Engenharia da Rotina #4: DO CAOS DAS TAREFAS AO PROJETO

### 854. Música para Lojas (UCBweagJM6Ll9nhZ5LcDirHQ)

- DB: subscribers=108000, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 10.8万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: obrigado
- Evidence lines:
  - 100.000 Thank you, teşekkürler, gracias, merci, danke, obrigado, obrigada, شكراً, grazie, спасибо, ありがとう, 감사합니다, cảm ơn, धन्यवाद, дякую, mulțumesc, благодаря, təşəkkürlər, ممنون, dank je, takk, tack, ขอบคุณ, terima kasih
  - 50.000 Thank you, teşekkürler, gracias, merci, danke, obrigado, obrigada, شكراً, grazie, спасибо, ありがとう, 감사합니다, cảm ơn, धन्यवाद, дякую, mulțumesc, благодаря, təşəkkürlər, ممنون, dank je, takk, tack, ขอบคุณ, terima kasih,

### 927. Anchoe (UC8ULH6DJE1pOyc3DduCTokA)

- DB: subscribers=2650, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 2650位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 976. Vem pra obra (UCdvHYFSi2NXrYeyVSyVhqoQ)

- DB: subscribers=17100, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.71万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, humor
- Evidence lines:
  - Dia de fazer as tampas das fossas #obra #pedreiro #humor #construcao
  - Fabricação da ferragem da viga baldrame
  - Marcação das sapatas
  - Marcação das paredes internas
  - Analisando o terreno antes de começar uma obra.acompanhe este projeto @vempraobra
  - Chapisco. a verdade sobre o chapisco! leia a descrição.
  - Precisa chapiscar antes de rebocar? Leia a descrição
  - Como fabricar terças para laje?

### 983. Ana Elisa Araujo-Bordado eletrônico e Costura  (UCbSYFDR_KenBdWgIHhdy00g)

- DB: subscribers=2150, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2150位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: aqui, muito, aprenda, aula
- Evidence lines:
  - Ana Elisa Araujo-Bordado eletrônico e Costura
  - @AnaElisaAraujo-Bordadoeletrôni
  - Aprenda bordado eletrônico e costura criativa de uma forma simples e descomplicada ❤️
  - PASSO A PASSO CHAVEIRO NOSSA SENHORA-MATRIZ DO PROJETO PORTA TERÇO NA BORDADEIRA
  - MARCA PÁGINA FEITO 100% NA BORDADEIRA- matriz grátis
  - BORDANDO APLIQUE EM TECIDO DE NOSSA SENHORA- MATRIZ LINDA E RÁPIDA
  - BORDANDO URSO EM APLIQUE SUPER FOFO- BORDADO ELETRÔNICO
  - AULA 4- COSTURANDO DOIS BARRADO TOALHAS SEMANA BORDADO- SEMANA DO BORDADO PERFEITO

### 990. Viaturas Bombeiros RJ (UCjKFtRF4osmX5h_w5Zj1YIQ)

- DB: subscribers=3370, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3370位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, vídeo, video, vídeos, videos
- Evidence lines:
  - Deslocamento Para Colisão 💥
  - Deslocamento para Colisão
  - Deslocamento Para Colisão
  - Deslocamento Para Colisão.
  - Deslocamento para Incêndio
  - Evento de Colisão 💥
  - Deslocamento Para Capotagem De Veículo #cbmerj #bombeiros
  - Deslocamento Para Incêndio
