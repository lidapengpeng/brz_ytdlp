# Browser random-1000 final review

Validation time: 2026-05-17 14:18-15:00 Asia/Shanghai

Input snapshot: `/Users/dapeng/Desktop/word/brz_ytdlp/results_browser_sample_snapshot_20260517_141811.db`

Sample: 1000 random rows from `channels` using `ORDER BY RANDOM() LIMIT 1000`.

Browser method: Playwright opened public YouTube `/about` pages for all 1000 rows. For the 32 initial weak rows, it opened `/videos` pages as a second pass. Chrome extension control was requested but unavailable (`Browser is not available: extension`), so Playwright browser automation was used.

## Sample Composition

- Total sample: 1000
- DB `country=Brasil/Brazil`: 854
- DB `country IS NULL`: 146

## Final Conservative Verdict

- PASS_STRICT_BROWSER_EVIDENCE: 957
- NEEDS_COUNTRY_EVIDENCE: 37
- NEEDS_PORTUGUESE_EVIDENCE: 1
- NEEDS_REVIEW: 5

## By DB Country

- country_BR: PASS_STRICT_BROWSER_EVIDENCE=849, NEEDS_PORTUGUESE_EVIDENCE=1, NEEDS_REVIEW=4
- country_NULL: PASS_STRICT_BROWSER_EVIDENCE=108, NEEDS_COUNTRY_EVIDENCE=37, NEEDS_REVIEW=1

## Interpretation

- Explicit `country=Brasil/Brazil` rows are very strong: 849/854 had browser-visible Brazil + Portuguese evidence under the conservative rule. The remaining 5 were not subscription failures; they were weak Portuguese/content evidence on the visible page.
- Missing-country rows are the real risk layer: 108/146 had strong browser-visible Brazil evidence, while 37 still had Portuguese/subscriber evidence but no direct Brazil/locality proof in the checked pages, and 1 remained generally weak.
- No sample showed subscriber count below 1000 in the browser evidence pass.
- A non-pass here means evidence was insufficient from the browser-visible text, not necessarily that the channel is false. Several weak rows look plausibly Brazilian but need a second evidence field before being treated as country-proven.

## Non-Pass Rows

### 17. Clara Nunes - Tema (UC9Gmegs9An5MqkRIHi7DjtQ)

- DB: subscribers=51100, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 5.12万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce
- Evidence lines:
  - كلارا نونيز هي مغنية برازيلية، ولدت في 12 أغسطس 1943 في Caetanópolis ‏ في البرازيل، وتوفيت في 2 أبريل 1983 في ريو دي جانيرو في البرازيل بسبب صدمة الحساسية.
  - Nação
  - As Forças Da Natureza
  - Os Primeiros Anos
  - Você Passa E Eu Acho Graça

### 34. Theus Vinicius Ofc (UCV3vXua-dnDXF_zok_fcqAQ)

- DB: subscribers=119000, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 12万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, bem-vindo, aqui, engenharia, família, familia
- Evidence lines:
  - Bem-vindo ao nosso universo de entrevistas vibrantes e curiosidades gerais! Aqui, mergulhamos em conversas animadas sobre uma variedade de temas, sempre com alegria e diversão. Descubra respostas incríveis, insights vali
  - Qual a sua profissão? #marinha #barco #militar #entrevista
  - Qual a sua profissão? #jesus #fe #trabalho  #entrevista
  - Qual é a raça do seu cachorro? #cachorro #dog #trabalho #entrevista
  - Qual a sua profissão? #casal #familia #viagem #entrevista

### 50. Gustavo Ferreira (UCrkkVWdZfbtbOZPrgUvcyiQ)

- DB: subscribers=1780, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1780位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, vídeo, video, vídeos, videos, conteúdo, conteudo, todos, dias, história, historia
- Evidence lines:
  - Me chamo Gustavo e falo sobre livros neste canal.
  - 12 LIVROS DE HISTÓRIA PARA 2026 #historia #books #listadelivros #historiacontemporánea #2026 #livros
  - 9 LIVROS CLÁSSICOS PARA LER EM 2026 #booktube #books #literaturaclassica #livrosclassicos #booktok
  - LIVROS RESENHADOS NO PRIMEIRO SEMESTRE #parte2 #resenhadelivros #books #booktube #livros #semestre
  - Bom dia pessoal, queria avisar vocês que essa semana será diferente... Postarei um vídeo todos os dias (seg-sex), todos correspondente a um capítulo do livro: O HOLOCAUSTO do Laurence Rees... Meu objetivo é terminar este

### 55. Papo Fora do Script, com Josias Junior (UCT6CMkA6gRt47CqCSumK22A)

- DB: subscribers=5790, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Bem-vindo ao PAPO FORA DO SCRIPT, com Josias Junior.
  - AMADEU LOUREIRO, uma história de vida!
  - Experiências, Mudanças e Propósito! A história de uma família que cruzou o planeta.
  - Por Que Estou Aqui no YouTube?
  - Quem foi GEDELTI GUEIROS? O que ninguém sabe sobre esse servo de Deus e grande líder.

### 123. MeryEllen Motta- casinha Motta (UCYS4tIibTOjU6baGI2aWWRw)

- DB: subscribers=1350, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1350位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: comédia, comedia, humor
- Evidence lines:
  - 🚧 Diário de obra🚧
  - Padrão ou poste?
  - Vem ver como eu faço o meu sushi em casa   #sushi #sushitime #sushiemcasa
  - Diário de obra 20/03
  - #obra #comedia #humor #memes #diy #casa

### 149. SNOWTER (UC6xQfp2yLMKZtYwxm63aojg)

- DB: subscribers=56000, country=Brasil, target_reason=country=Brazil
- Final verdict: `NEEDS_REVIEW`
- Initial browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_REVIEW`
- Visible subscribers: 5.6万位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 163. Sabedoria da Alma (UCWcrnCgJ4R6Fz4pvkTVqzNQ)

- DB: subscribers=41100, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - No Sabedoria da Alma, você encontrará reflexões profundas sobre a mente, a alma e o universo invisível que habita dentro de você. Este canal compartilha palestras que despertam a consciência, exploram o poder do inconsci
  - SE VOCÊ SE SENTE PERDIDO E VAZIO, ESTE VÍDEO VAI TE AJUDAR - Carl Jung Psicologia
  - O MOMENTO EM QUE VOCÊ SE ESCOLHE MUDA TODO O SEU DESTINO - Carl Jung Psicologia
  - COMO DEIXAR IR ALGUÉM QUE AINDA MORA EM VOCÊ - Carl Jung Psicologia
  - 10 CHAVES PARA CORTAR O VÍNCULO EMOCIONAL SEM DOR - Carl Jung Psicologia

### 242. Especialista Utilitário  (UCUNXDfAT9vpYLk55diJ9ffg)

- DB: subscribers=284000, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Especialista Utilitário
  - TER UMA TELA DE CINEMA EM CASA É MAIS BARATO QUE TELEVISÃO ( PROJETOR R15A )
  - O MELHOR ROBÔ QUE LIMPA CASA TÃO BEM COMO DONA DE CASA, VALE A PENA?

### 250. Ludmila Laiane (UCyGiNqFAmN1du-80k6J8lvw)

- DB: subscribers=10600, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Olá meninas, eu sou a Lud, vamos postar vários vídeos de dicas e tutoriais pra vcs, cuidados diários com o cabelo, penteados entre outros 😍.
  - Tutorial! Fazendo Babyliss no meu Cabelo, faça você mesma. #tutorial #façavocêmesmo
  - Passo a Passo para fazer Banho de Brilho com Coloração em casa/ faça você mesma
  - Dicas de cuidados com o cabelo loiro, loiro perfeito.

### 281. Nicolas TV (UCBVGJUPvLxMNpfK4ir2_ZLg)

- DB: subscribers=512000, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 51.2万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, bem-vindo, canal, inscreva, inscreva-se, vídeo, video, vídeos, videos, aqui, olá, ola, dança
- Evidence lines:
  - Nicolas TV
  - @canalnicolastv
  - Bem-vindo ao Nicolas TV! 🎥😄 Aqui você encontra os vídeos mais engraçados, divertidos e cheios de energia.
  - Fugindo da assombração
  - Cadê o bebê

### 282. Mr Cortes (UCX-dtsLAuXKO4U_KlyHhq3w)

- DB: subscribers=2710, country=Brasil, target_reason=country=Brazil
- Final verdict: `NEEDS_REVIEW`
- Initial browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_REVIEW`
- Visible subscribers: 2710位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 300. ClickHouse (UCODADD6kbJcv807t962udLQ)

- DB: subscribers=1290, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Empresa fabricante de casas modulares com método construtivo próprio, de grande rapidez de construção e altas prestações térmica e acústica.
  - Feng Shui ClickHouse | Conceito Feng Shui | Construção Modular
  - ClickHouse | O nosso método construtivo | Casas Modulares | Modular Architecture
  - ClickHouse | Conceito Neo | A constução de uma habitação modular desde o início
  - Apresentação ClickHouse Algarve | Casa Modelo Fuseta | Construção Modular

### 355. Manu Cordeiro (UCqzy1HcWWwZfXWJfNdma3Sg)

- DB: subscribers=8870, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 8870位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, seja, sejam, bem-vindo, canal, vídeo, video, aqui, muito
- Evidence lines:
  - ROTINA DE MÃE E DONA DE CASA| organização da casa, recebido da BUMMIS #maternidadereal #maternidade
  - COMPRAS DA SHOPEE PARA MEU BEBÊ DE 1 ano | comprei roupa e sapato na SHOPEE para meu bebê
  - Vlog | ROTINA DE MÃE - Passeio no shopping, organização da casa, mãe de um bebê de 1 ano
  - Vlog - COMO É A ROTINA REAL DE UMA MÃE | Mãe de primeira viagem
  - Usados e acabados do mês | Tudo que usei no meu bebê de 1 ano

### 377. Receitas Fáceis (UC388yvGzvXqDt7jfq3ov7uw)

- DB: subscribers=4240, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Receitas Fáceis
  - @receitasfaceis4243
  - Receitas Fáceis para o dia a dia 😀
  - Jiló frito crocante 😋
  - Molho de alho para churrasco super prático 😋😋😋

### 474. Rafaela de Sá Beauty (UCHI7jWKV9JNGHwlMwqJ0izw)

- DB: subscribers=2470, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Rafaela de Sá Beauty
  - Rotina, estética e propósito! 🤍
  - Deus faz tudo acontecer na HORA CERTA | essa mensagem vai se confirmar no seu coração
  - Lista básica de materiais | DESIGN DE SOBRANCELHAS
  - Uma mensagem do meu coração | Deus quer falar com você

### 485. Bya Artes em Bijuterias  (UCn2nzIuDDgOcLQEckcvRFTg)

- DB: subscribers=40300, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Transforme pérolas e miçangas em verdadeiras joias com tutoriais simples e criativos!
  - “Aprenda essa pulseira floral PERFEITA para vender muito 💜”.
  - Essa técnica simples deixa a pulseira com cara de joia!
  - Essa pulseira está vendendo MUITO! Aprenda agora
  - Por isso suas bijuterias NÃO vendem (erro no acabamento!)

### 493. RBHard Gamer (UCjV3ZxGRb5jyJevQewXhPwg)

- DB: subscribers=3530, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Sejam bem-vindos ao canal RBHard Gamer, um canal que traz vários temas sobre jogos!
  - Poppy Playtime Chapter 5 - Jogo Completo Sem Comentários| Dublado e legendado
  - Hello Neighbor 2 - Jogo Completo Sem Comentários
  - Silent Hill 2  -  Jogo Completo Sem Comentários - Legenda PT/BR
  - Poppy Playtime Chapter 4 - Jogo completo Dublado - Sem comentários

### 553. TheTruPlayers (UC521vgi-Kq7Lsh-zTziEbqg)

- DB: subscribers=3020, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Dois jovens aprendendo a viver nesse mundo virtual ! Comentários, unboxings, gameplays e tudo mais sobre games!
  - Unboxing Resident Evil Village Edição Padrão PS4
  - Unboxing Doom Eternal Edição Padrão PS4
  - Unboxing The Last of Us Part 2 Edição Padrão PS4
  - Detroit: Become Human DEMO - Negociação de refém!

### 571. Luana Ferreira gomes (UCIwCP2YioXPDaFBGbk0JnHQ)

- DB: subscribers=38200, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Vlog rotina da manhã 🤎✨️📸✅️
  - Primeiras comprinhas da casa nova 🏡🥹✨️
  - Preparando a marmita pro meu marido levar para o trabalho✨️🎥🦋#viralvideo #donadecasa #cozinha
  - Vlog rotina da manhã +limpeza e mercado ✨️🤎#fypシ゚viral #rotinadodia
  - Rotina de domingo morando aqui na Espanha🇪🇦🦋 #fypシ゚viral #explore #vidareal

### 579. Casinha da jessy (UC4c37vhQSU_MxMVY1NH7IWw)

- DB: subscribers=7250, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 7250位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, vídeo, video, aqui, todos, dias, muito, olá, ola, dicas
- Evidence lines:
  - @Casinha_da_jéssy
  - Olá pessoal !
  - instagram.com/jessy_jesus149?igsh=a2ZnNzRrMjJrYXJk
  - Vlog ✨ 4 dias sem lavar roupa 😵‍💫 não dei conta de terminar!! falei um pouquinho sobre meus filhos 💙
  - Fiz ovos de páscoa em casa 🐰🍫 continuação do vídeo anterior 😘

### 601. Mau&Ju (UCBX6ZcgBF7WJis66iU3czhA)

- DB: subscribers=2710, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Aqui nós vamos compartilhar com vocês um pouco da nossa vida nos EUA e trazer as melhores ideias de passeios e restaurantes.
  - PREÇOS DOS TÊNIS NO OUTLET MAIS BARATO DE ORLANO
  - Quantas atrações dá pra fazer em 1 dia na Universal? Fizemos dois parques!
  - POR ISSO QUE ESSA É A MELHOR ÉPOCA PRA VIR AQUI! (Flower & Garden 2026)
  - Fizemos um passeio na Universal que quase ninguém conhece (Portofino Bay)

### 606. YUCCA PLANTAS OFICIAL (UCHftyadDxp1IyQkMN6tCZfw)

- DB: subscribers=4780, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - YUCCA PLANTAS OFICIAL
  - @YUCCAOFICIAL
  - Bem-vindo ao Yucca Plantas Oficial, um canal criado para quem ama a natureza, cultiva com carinho suas plantinhas ou quer começar no maravilhoso mundo da jardinagem! Aqui você encontra dicas simples e práticas sobre cult
  - COMIGO NINGUÉM PODE - Folhagem gigante!!
  - Conheça a FLOR PARAQUEDAS!! Ceropegia sandersonii

### 614. Alex Quintanilha ins @alexqnt25 (UCNo0JBNM-58PgrDZpwPGzsg)

- DB: subscribers=13500, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - SIGA O CANAL TROPA @alexqnt25 no Instagram
  - SÓ RELÍQUIA 🚂❤️🤴🥇
  - Nós não tinha nada..💭 @Oruam Siga nossa página no Instagram @alexqnt25
  - Tz da Coronel com a minha tropa é NO LOVE ! 🧞‍♂️💎
  - Rock in Rio Mc Poze do Rodo faz apresentação histórica com Mc Bielzin confira ! 🔥🔥🔥🔥

### 644. JDS edits (UCsXIDcmikKMLOdy9qT8oGaw)

- DB: subscribers=1340, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Canal somente com intenção de divulgar boas músicas com clipes de minha criação e também divulgando algumas músicas de criação própria (Grupo Som e Magia),espero que gostem.
  - Zé Neto e Cristiano-Pai de Menina (Clipe)
  - Grupo Som e Magia- A Lareira (Clipe) -versão em Português BR  kamin - EMIN & JONY
  - Murilo Huff part. Zé Neto e Cristiano -Mente do Palhaço (Clipe)
  - Grupo Som e Magia- Eu Sei o Porquê (Clipe)

### 645. Banda Diesel (UC59enR3mGEs9ZDUKjgARCIA)

- DB: subscribers=1070, country=Brasil, target_reason=country=Brazil
- Final verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Initial browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 1070位订阅者
- Visible country row Brazil: True
- BR hits: brasil, belo horizonte
- PT hits: none
- Evidence lines:
  - Diesel - Belo Horizonte - Brasil
  - Diesel (Banda) ao Vivo | Show completo em Belo Horizonte
  - 巴西
- Second pass evidence lines:
  - Diesel - Belo Horizonte - Brasil
  - Diesel (Banda) ao Vivo | Show completo em Belo Horizonte

### 661. MILENA SILVA (UCh9ybVadD6JRCRJYs8kxFYA)

- DB: subscribers=11300, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.13万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, inscreva, aqui, todos, muito, olá, ola
- Evidence lines:
  - Vlogs e rotina/ Olá meus amores tudo bem? Me chamo Milena e te apresento um pouco da minha vida. Sou mãe, dona de casa e esposa que mora no interior do Maranhão,  se inscreva pra não perder naaadaaa🥰🤎🙏
  - COMO É A VIDA SIMPLES DE QUEM VIVE LONGE DE TUDO! REALIDADE…
  - NOSSA VERDADEIRA VIDA NO INTERIOR! COMO COMPRAMOS O BÁSICO POR AQUI…
  - EU NÃO ESPERAVA ENCONTRAR UM LUGAR TÃO LINDO ASSIM! RECANTO VERDE
  - COMO É MORAR NESSE “PARAÍSO” A REALIDADE DA MINHA ROTINA AQUI.

### 701. Rochristian (UCmY0yERVg95LJ8d8EKskQHw)

- DB: subscribers=20100, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2.01万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, vídeo, video, vídeos, videos, aqui, conteúdo, conteudo, todos, dias, muito, olá
- Evidence lines:
  - Se você já imaginou aqueles louvores clássicos que cantamos na igreja com um som mais pesado, cheio de guitarra, bateria e riffs marcantes, você está no lugar certo! Aqui no Rochristian, utilizamos inteligência artificia
  - Santo Pra Sempre - Versão Metal (Gabriel Guedes)
  - Aqui está uma versão baseada no som da banda Bad Omens dessa incrível composição do Gabriel Guedes, criado com IA com uma proposta bem diferente da música original, mas tentando ao máximo manter a mensagem da música!
  - ⚠️ O objetivo é apresentar um novo estilo para a música, sem alterar sua essência e mensagem.
  - 🎸 Criação com IA: Usamos o Suno AI para transformar o estilo original e ver como soaria em uma pegada rock!

### 709. WA Alimentos (UC4J2JrDn8D6OHj-Gy8_WR8w)

- DB: subscribers=3820, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3820位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: canal, vídeo, video, conteúdo, conteudo, dicas
- Evidence lines:
  - Dicas no nosso canal do YouTube sobre cortes e temperos!
  - FILÉ DO PEIXE DE PIRARARA... VÍDEO DETALHADO ESTAR NO CONTEÚDO DO MEU CANAL.
- Second pass evidence lines:
  - Dicas no nosso canal do YouTube sobre cortes e temperos!
  - TEMPERO BATIDO DO PEIXE FILÉ DE PIRARARA... DICAS DO CORTE DO PEIXE ESTA LA NO CANAL!
  - Dicas de cortes do PEIXE PIRARARA, para assar na brasa ou forno. Dica do tempero parte 2 no canal.
  - Fatiando cupim bola maturato para o churrasco

### 730. ANIMAL LEGENDS (UCujjjVhNKwi32EJLHqk_0xg)

- DB: subscribers=39300, country=Brasil, target_reason=country=Brazil
- Final verdict: `NEEDS_REVIEW`
- Initial browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_REVIEW`
- Visible subscribers: 3.93万位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 765. MarinaMarvet  (UCp4pZZuJaIPKr8mW7yyHgQQ)

- DB: subscribers=7710, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Aprenda aqui como faço algumas das minhas artes, animais de biscuit, miniaturas e customizações!!
  - Customizei o cavalinho igual o embaixador do pepê.
  - Fiz uma miniatura diferente, uma nova raça de cavalo.
  - Como fazer cabeçada de EVA para seus cavalos de brinquedo
  - Cavalo árabe customizado

### 771. Som da Fé  (UC-SEHXoDYxs9rzUuU6NVOpA)

- DB: subscribers=16500, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.65万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, canal, aqui, oficial, música, musica
- Evidence lines:
  - Som da Fé
  - @oficialsomdafe
  - A música é algo que me segue desde criança, e a Palavra de Deus foi o que mudou minha vida. Eu tenho como missão nesse canal transmitir a Palavra de Deus através de música.
  - Deus… Eu Fiz Tudo Certo. Então Por Que Ainda Estou Sofrendo? 💔
  - "Meu Pai Nunca Disse Eu Te Amo  - Blues de Oração "

### 822. Victor Molin - Produzindo Conteúdo com seu iPhone! (UCcnh6s19XPF4dypShGWyfxA)

- DB: subscribers=25500, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Victor Molin - Produzindo Conteúdo com seu iPhone!
  - Aprenda a Fotografar e Filmar Melhor Com Seu iPhoen!
  - Configurações IDEAIS do iPhone 14, Pro e Pro Max (iOS 26) 📱
  - Configurações IDEAIS do iPhone 15, Pro e Pro Max (iOS 26) 📱
  - Como pensar como fotógrafo (mesmo sendo leigo)

### 827. EletrocarReck Dia A Dia Da Oficina (UC5NajJulpNiNqGL7ErI7yYA)

- DB: subscribers=6500, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Em nosso canal mostraremos o Dia A Dia de uma auto elétrica,a parte bonita,boa e também as dificuldades do dia-a-dia.Nossos atendimentos externos, além de mostrar como nesse mundo existem pessoas boas...
  - Três corola no Mesmo Dia! Coincidência?
  - A oficina está Lotada! Muitos Desafios nesse dia!
  - Eco Sport Não Funciona Com Motor Quente (Resolvido)
  - Auto Elétrica Passando conhecimentos Pra Você

### 830. Eternos Louvores Oficial (UCR7qpuGjlTYZROqBjK0JVcw)

- DB: subscribers=1500, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1500位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: oficial, música, musica
- Evidence lines:
  - Eternos Louvores Oficial
  - @eternoslouvoresoficial-1993el
  - Somos uma Banda que leva a Palavra de Deus,através das canções
  - Minha Benção/ Eu Sou livre (Couver/Cassiane/Fernandinho)
  - Videira (Couver) - Eternos Louvores e Ministério de Louvor da IMW Vila Olímpia (Guapimirim)

### 852. SOU ESTRATEGISTA (UCwtlUWslUU9Lcr0dJsKeXBg)

- DB: subscribers=1690, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - A gente vive o que ensina — e aqui te mostramos como você também pode viver com mais intenção, organização e liberdade.
  - Engenharia da Rotina #4: DO CAOS DAS TAREFAS AO PROJETO
  - Por que eu SUMI dos vídeos curtos? O que mudou no projeto
  - Engenharia da Rotina #03: O PODER DOS BOTÕES NO NOTION
  - Prontuário Pro #4: DASHBOARD PROFISSIONAL

### 854. Música para Lojas (UCBweagJM6Ll9nhZ5LcDirHQ)

- DB: subscribers=108000, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_REVIEW`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_REVIEW`
- Visible subscribers: 10.8万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: obrigado
- Evidence lines:
  - 100.000 Thank you, teşekkürler, gracias, merci, danke, obrigado, obrigada, شكراً, grazie, спасибо, ありがとう, 감사합니다, cảm ơn, धन्यवाद, дякую, mulțumesc, благодаря, təşəkkürlər, ممنون, dank je, takk, tack, ขอบคุณ, terima kasih
  - 50.000 Thank you, teşekkürler, gracias, merci, danke, obrigado, obrigada, شكراً, grazie, спасибо, ありがとう, 감사합니다, cảm ơn, धन्यवाद, дякую, mulțumesc, благодаря, təşəkkürlər, ممنون, dank je, takk, tack, ขอบคุณ, terima kasih,

### 904. Rosy aventura FC (UC5qgzE8YyhUZGmZH2aQWB9A)

- DB: subscribers=195000, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 19.5万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vocês, voces, canal, inscreva, oficial, todos
- Evidence lines:
  - Este canal é um canal de divulgação do canal oficial da Rosy aventura. Se inscreva se neste canal corre lá e também se inscreve no canal oficial que Deus abençoe a todos
  - NUNCA ANTES NO CANAL ESPÍRITO CHAMA ROSY PARA TOMAR CAFÉ - SPIRITBOX
  - NINGUÉM ESPERAVA O QUE ESS4 MULHER FEZ - SPIRITBOX
  - A COBRANÇA FOI FORTE E A ROSY FICOU SEM CHÃO - SPIRITBOX
  - ELE ESTAVA LÁ NO ESCURO NOS VIGIANDO - SPIRITBOX

### 927. Anchoe (UC8ULH6DJE1pOyc3DduCTokA)

- DB: subscribers=2650, country=Brasil, target_reason=country=Brazil
- Final verdict: `NEEDS_REVIEW`
- Initial browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_REVIEW`
- Visible subscribers: 2650位订阅者
- Visible country row Brazil: True
- BR hits: none
- PT hits: none
- Evidence lines:
  - 巴西

### 940. Kyeøruh (UCSdmEJfgd_vGWvTIH94ddaw)

- DB: subscribers=10900, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.1万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, seja, canal, vídeo, video, olá, ola, aprenda, história, historia
- Evidence lines:
  - Fala aí, eu sou o Kyeoruh.
  - Se tem CONCORRÊNCIA... eu serei a DESISTÊNCIA.
  - Quando a sua MORALIDADE se torna sua MALDIÇÃO
  - A DEFINIÇÃO mais pura de AMOR MASCULINO em uma OBRA!!
  - Orange – O PESO das ESCOLHAS NÃO FEITAS

### 976. Vem pra obra (UCdvHYFSi2NXrYeyVSyVhqoQ)

- DB: subscribers=17100, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Analisando o terreno antes de começar uma obra.acompanhe este projeto @vempraobra
  - Chapisco. a verdade sobre o chapisco! leia a descrição.
  - Precisa chapiscar antes de rebocar? Leia a descrição
  - Como fabricar terças para laje?
  - Quais são as medidas do andaime suspenso?

### 978. Diário em Vlog (UCESIM5mxHiEBtGl2FN8bTnQ)

- DB: subscribers=2040, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2040位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: bem-vindo, aqui, dias, dança, receitas
- Evidence lines:
  - Diário em Vlog
  - Bem-vindo ao Diário em Vlog 🌿
  - Dias Calmos de Outono e Pequenas Alegrias | Novo Projeto e Comprinhas pra Casa | Vlog Silencioso 🌷
  - Meu primeiro Casaco de Crochê 🧶| finalmente terminei 🤍| Será que ficou bom? 🧶🤍
  - Rotina real de mãe | cuidados, café e um dia simples em casa 🤍

### 983. Ana Elisa Araujo-Bordado eletrônico e Costura  (UCbSYFDR_KenBdWgIHhdy00g)

- DB: subscribers=2150, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Second pass `/videos` verdict: `NEEDS_COUNTRY_EVIDENCE`
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
- Second pass evidence lines:
  - Ana Elisa Araujo-Bordado eletrônico e Costura
  - @AnaElisaAraujo-Bordadoeletrôni
  - Aprenda bordado eletrônico e costura criativa de uma forma simples e descomplicada ❤️
  - PASSO A PASSO CHAVEIRO NOSSA SENHORA-MATRIZ DO PROJETO PORTA TERÇO NA BORDADEIRA
  - MARCA PÁGINA FEITO 100% NA BORDADEIRA- matriz grátis

### 1000. Luiz Paixão (UCxkK_t_6hS48C1ZTC4n1gbw)

- DB: subscribers=3080, country=None, target_reason=country=None,lang=pt
- Final verdict: `NEEDS_COUNTRY_EVIDENCE`
- Initial browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3080位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: canal, vídeo, video, vídeos, videos, aqui, todos, muito, muita, obrigado, comédia, comedia, humor
- Evidence lines:
  - Luiz Paixão
  - @LuizPaixão
  - Canal destinado a Rap e Comedia
  - LIFESTYLE DE UM COMEDIANTE - LUIZ PAIXÃO
  - Esse aqui é o primeiro vídeo da série Rap Comedy, onde vou trazer vários vídeos de Rap com Stand up. Esse é o primeiro e o mais especial de todos, pois é o que conta o que vivi pra chegar até aqui.
