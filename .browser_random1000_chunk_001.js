
(async page => {
  const rows = [{"sample_index": 55, "channel_id": "UCT6CMkA6gRt47CqCSumK22A", "name": "Papo Fora do Script, com Josias Junior", "handle": "@papoforadoscript", "subscribers": 5790, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCT6CMkA6gRt47CqCSumK22A/videos"}, {"sample_index": 104, "channel_id": "UCR5B6B3W3G7FFntU1cng3fw", "name": "BRISA7 FF", "handle": "@brisa7ff", "subscribers": 27100, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCR5B6B3W3G7FFntU1cng3fw/videos"}, {"sample_index": 149, "channel_id": "UC6xQfp2yLMKZtYwxm63aojg", "name": "SNOWTER", "handle": "@Snowter_", "subscribers": 56000, "country": "Brasil", "target_reason": "country=Brazil", "url": "https://www.youtube.com/channel/UC6xQfp2yLMKZtYwxm63aojg/videos"}, {"sample_index": 163, "channel_id": "UCWcrnCgJ4R6Fz4pvkTVqzNQ", "name": "Sabedoria da Alma", "handle": "@SabedoriadaAlma777", "subscribers": 41100, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCWcrnCgJ4R6Fz4pvkTVqzNQ/videos"}, {"sample_index": 242, "channel_id": "UCUNXDfAT9vpYLk55diJ9ffg", "name": "Especialista Utilitário ", "handle": "@especialistautilitario", "subscribers": 284000, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCUNXDfAT9vpYLk55diJ9ffg/videos"}, {"sample_index": 250, "channel_id": "UCyGiNqFAmN1du-80k6J8lvw", "name": "Ludmila Laiane", "handle": "@ludmilalaianee", "subscribers": 10600, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCyGiNqFAmN1du-80k6J8lvw/videos"}, {"sample_index": 282, "channel_id": "UCX-dtsLAuXKO4U_KlyHhq3w", "name": "Mr Cortes", "handle": "@MrCortesIQ", "subscribers": 2710, "country": "Brasil", "target_reason": "country=Brazil", "url": "https://www.youtube.com/channel/UCX-dtsLAuXKO4U_KlyHhq3w/videos"}, {"sample_index": 300, "channel_id": "UCODADD6kbJcv807t962udLQ", "name": "ClickHouse", "handle": "@clickhouse8913", "subscribers": 1290, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCODADD6kbJcv807t962udLQ/videos"}, {"sample_index": 377, "channel_id": "UC388yvGzvXqDt7jfq3ov7uw", "name": "Receitas Fáceis", "handle": "@receitasfaceis4243", "subscribers": 4240, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UC388yvGzvXqDt7jfq3ov7uw/videos"}, {"sample_index": 474, "channel_id": "UCHI7jWKV9JNGHwlMwqJ0izw", "name": "Rafaela de Sá Beauty", "handle": "@rafaeladesabeauty", "subscribers": 2470, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCHI7jWKV9JNGHwlMwqJ0izw/videos"}, {"sample_index": 485, "channel_id": "UCn2nzIuDDgOcLQEckcvRFTg", "name": "Bya Artes em Bijuterias ", "handle": "@byaartesembijuterias", "subscribers": 40300, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCn2nzIuDDgOcLQEckcvRFTg/videos"}, {"sample_index": 493, "channel_id": "UCjV3ZxGRb5jyJevQewXhPwg", "name": "RBHard Gamer", "handle": "@RBHard", "subscribers": 3530, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCjV3ZxGRb5jyJevQewXhPwg/videos"}, {"sample_index": 553, "channel_id": "UC521vgi-Kq7Lsh-zTziEbqg", "name": "TheTruPlayers", "handle": "@TheTruPlayers", "subscribers": 3020, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UC521vgi-Kq7Lsh-zTziEbqg/videos"}, {"sample_index": 571, "channel_id": "UCIwCP2YioXPDaFBGbk0JnHQ", "name": "Luana Ferreira gomes", "handle": "@Luannagomes.f", "subscribers": 38200, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCIwCP2YioXPDaFBGbk0JnHQ/videos"}, {"sample_index": 577, "channel_id": "UCo4wdAdhIh6FGRBegRoq0sA", "name": "sheyla lanna", "handle": "@sheylalanna6177", "subscribers": 2220, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCo4wdAdhIh6FGRBegRoq0sA/videos"}, {"sample_index": 601, "channel_id": "UCBX6ZcgBF7WJis66iU3czhA", "name": "Mau&Ju", "handle": "@maueju", "subscribers": 2710, "country": null, "target_reason": "country=None,lang=pt", "url": "https://www.youtube.com/channel/UCBX6ZcgBF7WJis66iU3czhA/videos"}];
  const BR_TERMS = ["brasil", "brazil", "brasileiro", "brasileira", "brasileiros", "brasileiras", "brasilia", "brasília", "com.br", "gov.br", ".br", "pix", "cnpj", "cpf", "cep", "r$", "sao paulo", "são paulo", "paulista", "rio de janeiro", "carioca", "belo horizonte", "minas gerais", "mineiro", "mineira", "porto alegre", "rio grande do sul", "gaucho", "gaúcho", "curitiba", "parana", "paraná", "florianopolis", "florianópolis", "santa catarina", "sorocaba", "campinas", "santos", "ribeirão preto", "ribeirao preto", "salvador", "bahia", "baiano", "baiana", "recife", "pernambuco", "fortaleza", "ceara", "ceará", "goiania", "goiânia", "goias", "goiás", "belem", "belém", "manaus", "amazonas", "vitoria", "vitória", "espirito santo", "espírito santo", "maceio", "maceió", "aracaju", "natal", "joao pessoa", "joão pessoa", "teresina", "sao luis", "são luís", "campo grande", "cuiaba", "cuiabá", "nordeste", "nordestino", "sertanejo", "forró", "forro", "pagode", "samba", "funk carioca", "brega", "pisadinha", "piseiro", "arrocha", "axé", "axe", "flamengo", "corinthians", "palmeiras", "vasco", "botafogo", "fluminense", "gremio", "grêmio", "internacional", "cruzeiro", "atlético mineiro", "atletico mineiro", "bahia", "sport recife", "santa cruz", "náutico", "nautico", "fortaleza ec", "sus", "enem", "oab", "fgts", "inss", "senai", "senac", "sebrae", "sesc", "prefeitura", "câmara municipal", "camara municipal", "diário oficial", "diario oficial", "clt", "mei", "ibge", "petrobras", "embrapa", "caixa econômica", "caixa economica", "banco do brasil", "b3", "mini dólar", "mini dolar", "mini-índice", "mini-indice", "pataxó", "pataxo", "yanomami", "guarani", "tupiniquim", "kamayura", "xingu"];
  const PT_TERMS = ["você", "voce", "vocês", "voces", "seja", "sejam", "bem-vindo", "bem vindo", "canal", "inscreva", "inscreva-se", "vídeo", "video", "vídeos", "videos", "aqui", "conteúdo", "conteudo", "oficial", "todos", "dias", "muito", "muita", "olá", "ola", "obrigado", "aprenda", "educação", "física", "dança", "vendas", "música", "musica", "engenharia", "receitas", "comédia", "comedia", "humor", "família", "familia", "notícias", "noticias", "futebol", "aula", "aulas", "dicas", "história", "historia", "brinquedos", "crianças", "criancas"];
  const norm = s => String(s || '').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const subRe = /((?:\d+[\.,]?\d*|\d+)\s*(?:万|亿)?\s*位订阅者|(?:\d+[\.,]?\d*)\s*(?:K|M|mi|mil)?\s*(?:subscribers|inscritos))/i;
  const chineseRe = /[\u4e00-\u9fff]/;
  const dddRe = /\(?\b(?:11|12|13|14|15|16|17|18|19|21|22|24|27|28|31|32|33|34|35|37|38|41|42|43|44|45|46|47|48|49|51|53|54|55|61|62|63|64|65|66|67|68|69|71|73|74|75|77|79|81|82|83|84|85|86|87|88|89|91|92|93|94|95|96|97|98|99)\)?\s?9?\d{4}[-\s]?\d{4}\b/;

  if (!globalThis.__brzRouteSet) {
    await page.route('**/*', route => {
      const type = route.request().resourceType();
      if (['image', 'media', 'font'].includes(type)) return route.abort();
      return route.continue();
    });
    globalThis.__brzRouteSet = true;
  }

  function analyze(row, text, finalUrl, title) {
    const lines = String(text || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const nt = norm(text);
    const brHits = BR_TERMS.filter(t => nt.includes(norm(t))).slice(0, 16);
    const ptHits = PT_TERMS.filter(t => nt.includes(norm(t))).slice(0, 16);
    const visibleCountryBrazil = lines.some(l => l === '巴西' || /^brasil$/i.test(l) || /^brazil$/i.test(l));
    const visibleSubscribers = (String(text || '').match(subRe) || [''])[0];
    const hasBrazilPhone = dddRe.test(String(text || ''));
    const hasDiacritics = /[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]/.test(String(text || ''));
    const brOk = visibleCountryBrazil || brHits.length > 0 || hasBrazilPhone;
    const ptOk = ptHits.length > 0 || hasDiacritics;
    const subsOk = Boolean(visibleSubscribers) || Number(row.subscribers || 0) >= 1000;
    let verdict = 'NEEDS_REVIEW';
    if (subsOk && brOk && ptOk) verdict = 'PASS_BROWSER_EVIDENCE';
    else if (subsOk && ptOk && !brOk) verdict = 'NEEDS_COUNTRY_EVIDENCE';
    else if (subsOk && brOk && !ptOk) verdict = 'NEEDS_PORTUGUESE_EVIDENCE';

    const evidence = [];
    for (const raw of lines) {
      const line = raw.length > 220 ? raw.slice(0, 220) : raw;
      const low = norm(line);
      const latin = /[A-Za-zÀ-ÿ]/.test(line);
      const brLine = BR_TERMS.some(t => low.includes(norm(t))) || dddRe.test(line) || line === '巴西';
      const ptLine = PT_TERMS.some(t => low.includes(norm(t))) || /[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔÀ]/.test(line);
      if ((latin || line === '巴西') && (brLine || ptLine) && !evidence.includes(line)) evidence.push(line);
      if (evidence.length >= 8) break;
    }
    return {
      sample_index: row.sample_index,
      channel_id: row.channel_id,
      name: row.name,
      handle: row.handle,
      db_subscribers: row.subscribers,
      db_country: row.country,
      db_target_reason: row.target_reason,
      requested_url: row.url,
      final_url: finalUrl,
      title,
      visible_subscribers: visibleSubscribers,
      visible_country_brazil: visibleCountryBrazil,
      browser_br_hits: brHits,
      browser_pt_hits: ptHits,
      has_brazil_phone: hasBrazilPhone,
      evidence_lines: evidence,
      verdict,
      text_len: String(text || '').length,
      text_preview: String(text || '').slice(0, 900),
    };
  }

  const out = [];
  for (const row of rows) {
    try {
      await page.goto(row.url, { waitUntil: 'domcontentloaded', timeout: 25000 });
      await page.waitForTimeout(1200);
      let text = await page.evaluate(() => document.body ? document.body.innerText : '');
      if (!text || text.length < 500) {
        await page.waitForTimeout(1600);
        text = await page.evaluate(() => document.body ? document.body.innerText : '');
      }
      out.push(analyze(row, text, page.url(), await page.title()));
    } catch (e) {
      out.push({
        sample_index: row.sample_index,
        channel_id: row.channel_id,
        name: row.name,
        handle: row.handle,
        db_subscribers: row.subscribers,
        db_country: row.country,
        db_target_reason: row.target_reason,
        requested_url: row.url,
        verdict: 'FETCH_ERROR',
        error: String(e && e.message || e).slice(0, 500),
      });
    }
  }
  return out;
})
