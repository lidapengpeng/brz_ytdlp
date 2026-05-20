# Browser random-1000 validation report

Validation time: 2026-05-17 15:17:03 Asia/Shanghai

Method: 1000 rows were randomly sampled from the SQLite snapshot, then each public YouTube `/about` page was opened in a Playwright browser session. The verdict uses browser-rendered text, not only DB fields.

## Summary

- Sample size: 32
- NEEDS_COUNTRY_EVIDENCE: 18
- PASS_BROWSER_EVIDENCE: 8
- NEEDS_REVIEW: 4
- NEEDS_PORTUGUESE_EVIDENCE: 2

## By DB Country

- country_NULL: NEEDS_COUNTRY_EVIDENCE=18, PASS_BROWSER_EVIDENCE=8, NEEDS_REVIEW=1
- country_BR: NEEDS_REVIEW=3, NEEDS_PORTUGUESE_EVIDENCE=2

## Non-Pass Samples

### 55. Papo Fora do Script, com Josias Junior (UCT6CMkA6gRt47CqCSumK22A)

- DB: subscribers=5790, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 5860位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: bem-vindo, aqui, dança, família, familia, história, historia
- Evidence lines:
  - Bem-vindo ao PAPO FORA DO SCRIPT, com Josias Junior.
  - AMADEU LOUREIRO, uma história de vida!
  - Experiências, Mudanças e Propósito! A história de uma família que cruzou o planeta.
  - Por Que Estou Aqui no YouTube?
  - Quem foi GEDELTI GUEIROS? O que ninguém sabe sobre esse servo de Deus e grande líder.

### 149. SNOWTER (UC6xQfp2yLMKZtYwxm63aojg)

- DB: subscribers=56000, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_REVIEW`
- Visible subscribers: 5.6万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: none
- Evidence lines:

### 242. Especialista Utilitário  (UCUNXDfAT9vpYLk55diJ9ffg)

- DB: subscribers=284000, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 28.4万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: none
- Evidence lines:
  - Especialista Utilitário
  - TER UMA TELA DE CINEMA EM CASA É MAIS BARATO QUE TELEVISÃO ( PROJETOR R15A )
  - O MELHOR ROBÔ QUE LIMPA CASA TÃO BEM COMO DONA DE CASA, VALE A PENA?

### 250. Ludmila Laiane (UCyGiNqFAmN1du-80k6J8lvw)

- DB: subscribers=10600, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1.06万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vídeo, video, vídeos, videos, olá, ola, dicas
- Evidence lines:
  - Olá meninas, eu sou a Lud, vamos postar vários vídeos de dicas e tutoriais pra vcs, cuidados diários com o cabelo, penteados entre outros 😍.
  - Tutorial! Fazendo Babyliss no meu Cabelo, faça você mesma. #tutorial #façavocêmesmo
  - Passo a Passo para fazer Banho de Brilho com Coloração em casa/ faça você mesma
  - Dicas de cuidados com o cabelo loiro, loiro perfeito.

### 282. Mr Cortes (UCX-dtsLAuXKO4U_KlyHhq3w)

- DB: subscribers=2710, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_REVIEW`
- Visible subscribers: 2710位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: none
- Evidence lines:

### 300. ClickHouse (UCODADD6kbJcv807t962udLQ)

- DB: subscribers=1290, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1290位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: vídeo, video
- Evidence lines:
  - Empresa fabricante de casas modulares com método construtivo próprio, de grande rapidez de construção e altas prestações térmica e acústica.
  - Feng Shui ClickHouse | Conceito Feng Shui | Construção Modular
  - ClickHouse | O nosso método construtivo | Casas Modulares | Modular Architecture
  - ClickHouse | Conceito Neo | A constução de uma habitação modular desde o início
  - Apresentação ClickHouse Algarve | Casa Modelo Fuseta | Construção Modular
  - ClickHouse | Arquitetura Modular | As fases de uma construção modular
  - ClickHouse | Conceito Safe | Construção modular pensada na sua segurança e conforto|
  - ClickHouse Vídeo Promocional | Arquitetura Modular

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
- PT hits: você, voce, muito, olá, ola, aprenda
- Evidence lines:
  - Transforme pérolas e miçangas em verdadeiras joias com tutoriais simples e criativos!
  - “Aprenda essa pulseira floral PERFEITA para vender muito 💜”.
  - Essa técnica simples deixa a pulseira com cara de joia!
  - Essa pulseira está vendendo MUITO! Aprenda agora
  - Por isso suas bijuterias NÃO vendem (erro no acabamento!)
  - 💎 “Brincos elegantes feitos à mão: fácil, lindo e lucrativo!”
  - VOCÊ NÃO VAI ACREDITAR nesse anel de pérola com arame 😱 (fácil demais!)
  - “Aprenda esse Choker de Pérolas do ZERO (e comece a lucrar com bijuterias hoje!)”

### 493. RBHard Gamer (UCjV3ZxGRb5jyJevQewXhPwg)

- DB: subscribers=3530, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3530位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: seja, sejam, bem-vindo, canal
- Evidence lines:
  - Sejam bem-vindos ao canal RBHard Gamer, um canal que traz vários temas sobre jogos!
  - Poppy Playtime Chapter 5 - Jogo Completo Sem Comentários| Dublado e legendado
  - Hello Neighbor 2 - Jogo Completo Sem Comentários
  - Silent Hill 2  -  Jogo Completo Sem Comentários - Legenda PT/BR
  - Poppy Playtime Chapter 4 - Jogo completo Dublado - Sem comentários
  - Poppy Playtime Chapter 1 - Jogo Completo Sem Comentário
  - Poppy Playtime Chapter 2 - Jogo completo Sem Comentários

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
- PT hits: você, voce, bem-vindo, canal, aqui, oficial, muita, olá, ola, aprenda, dicas
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
- PT hits: você, voce, canal, oficial
- Evidence lines:
  - SIGA O CANAL TROPA @alexqnt25 no Instagram
  - SÓ RELÍQUIA 🚂❤️🤴🥇
  - Nós não tinha nada..💭 @Oruam Siga nossa página no Instagram @alexqnt25
  - Tz da Coronel com a minha tropa é NO LOVE ! 🧞‍♂️💎
  - Rock in Rio Mc Poze do Rodo faz apresentação histórica com Mc Bielzin confira ! 🔥🔥🔥🔥
  - Prévia Filipe Ret - Caio Luccas - Anezzi - Visão de Cria 2 (Prod. DALLASS)#nadamal
  - OROCHI, CAIO LUCCAS - "JADEN PICON" (ÁUDIO PRÉVIA)
  - Tz da Coronel - "SEM OPÇÃO"(GUIA VAZADA)

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
  - Murilo Huff part. Zé Neto e Cristiano -Mente do Palhaço (Clipe)
  - Grupo Som e Magia- Eu Sei o Porquê (Clipe)
  - Zé Neto e Cristiano part. Jorge e Mateus- Metade Dela (Clipe)
  - Grupo Som e Magia- Aberração (Clipe)
  - PedroKê-Por que você tá fazendo isso? (Clipe)

### 645. Banda Diesel (UC59enR3mGEs9ZDUKjgARCIA)

- DB: subscribers=1070, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 1070位订阅者
- Visible country row Brazil: False
- BR hits: brasil, belo horizonte
- PT hits: none
- Evidence lines:
  - Diesel - Belo Horizonte - Brasil
  - Diesel (Banda) ao Vivo | Show completo em Belo Horizonte

### 709. WA Alimentos (UC4J2JrDn8D6OHj-Gy8_WR8w)

- DB: subscribers=3820, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 3820位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: canal, olá, ola, dicas
- Evidence lines:
  - Dicas no nosso canal do YouTube sobre cortes e temperos!
  - TEMPERO BATIDO DO PEIXE FILÉ DE PIRARARA... DICAS DO CORTE DO PEIXE ESTA LA NO CANAL!
  - Dicas de cortes do PEIXE PIRARARA, para assar na brasa ou forno. Dica do tempero parte 2 no canal.
  - Fatiando cupim bola maturato para o churrasco

### 730. ANIMAL LEGENDS (UCujjjVhNKwi32EJLHqk_0xg)

- DB: subscribers=39300, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_PORTUGUESE_EVIDENCE`
- Visible subscribers: 3.93万位订阅者
- Visible country row Brazil: False
- BR hits: sus
- PT hits: none
- Evidence lines:

### 765. MarinaMarvet  (UCp4pZZuJaIPKr8mW7yyHgQQ)

- DB: subscribers=7710, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 7720位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: aqui, aprenda
- Evidence lines:
  - Aprenda aqui como faço algumas das minhas artes, animais de biscuit, miniaturas e customizações!!
  - Customizei o cavalinho igual o embaixador do pepê.
  - Fiz uma miniatura diferente, uma nova raça de cavalo.
  - Como fazer cabeçada de EVA para seus cavalos de brinquedo
  - Cavalo árabe customizado
  - Restauração de cavalinho de brinquedo.
  - Fiz um cavalo de vaquejada, olha só como ficou!!

### 822. Victor Molin - Produzindo Conteúdo com seu iPhone! (UCcnh6s19XPF4dypShGWyfxA)

- DB: subscribers=25500, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 2.55万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: vídeo, video, vídeos, videos, conteúdo, conteudo, aprenda, aula
- Evidence lines:
  - Victor Molin - Produzindo Conteúdo com seu iPhone!
  - Aprenda a Fotografar e Filmar Melhor Com Seu iPhoen!
  - Configurações IDEAIS do iPhone 14, Pro e Pro Max (iOS 26) 📱
  - Configurações IDEAIS do iPhone 15, Pro e Pro Max (iOS 26) 📱
  - Como pensar como fotógrafo (mesmo sendo leigo)
  - O Fotógrafo Fantasma de São Francisco 📷
  - Configurações IDEAIS do iPhone 11, Pro e Pro Max (iOS 26) 📱
  - AULA - APRENDENDO A USAR O MODO PANORAMA

### 827. EletrocarReck Dia A Dia Da Oficina (UC5NajJulpNiNqGL7ErI7yYA)

- DB: subscribers=6500, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 6500位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, canal, muito, olá, ola, história, historia
- Evidence lines:
  - Em nosso canal mostraremos o Dia A Dia de uma auto elétrica,a parte bonita,boa e também as dificuldades do dia-a-dia.Nossos atendimentos externos, além de mostrar como nesse mundo existem pessoas boas...
  - Três corola no Mesmo Dia! Coincidência?
  - A oficina está Lotada! Muitos Desafios nesse dia!
  - Eco Sport Não Funciona Com Motor Quente (Resolvido)
  - Auto Elétrica Passando conhecimentos Pra Você
  - Problema vidro Elétrico Eco sport Resolvido na Prática
  - Focus Não Marca Combustível(Resolvido)odômetro oscilando
  - Na Auto Elétrica a Correria tomou conta do nosso dia

### 852. SOU ESTRATEGISTA (UCwtlUWslUU9Lcr0dJsKeXBg)

- DB: subscribers=1690, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_COUNTRY_EVIDENCE`
- Visible subscribers: 1690位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: você, voce, vídeo, video, vídeos, videos, aqui, engenharia
- Evidence lines:
  - A gente vive o que ensina — e aqui te mostramos como você também pode viver com mais intenção, organização e liberdade.
  - Engenharia da Rotina #4: DO CAOS DAS TAREFAS AO PROJETO
  - Por que eu SUMI dos vídeos curtos? O que mudou no projeto
  - Engenharia da Rotina #03: O PODER DOS BOTÕES NO NOTION
  - Prontuário Pro #4: DASHBOARD PROFISSIONAL
  - Prontuário Pro #3: PROGRESSO REAL
  - Engenharia da Rotina #2: MEDIDOR DE ENERGIA
  - Engenharia da Rotina #1: NOTION DO ZERO

### 854. Música para Lojas (UCBweagJM6Ll9nhZ5LcDirHQ)

- DB: subscribers=108000, country=None, target_reason=country=None,lang=pt
- Browser verdict: `NEEDS_REVIEW`
- Visible subscribers: 10.8万位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: none
- Evidence lines:

### 927. Anchoe (UC8ULH6DJE1pOyc3DduCTokA)

- DB: subscribers=2650, country=Brasil, target_reason=country=Brazil
- Browser verdict: `NEEDS_REVIEW`
- Visible subscribers: 2650位订阅者
- Visible country row Brazil: False
- BR hits: none
- PT hits: none
- Evidence lines:

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
