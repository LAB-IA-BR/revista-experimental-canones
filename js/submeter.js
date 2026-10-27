(function () {
  var form = document.getElementById("proposta");
  var status = document.getElementById("form-status");
  var submit = document.getElementById("enviar");
  if (!form || !status || !submit) return;

  var ENDPOINT = "https://formsubmit.co/ajax/orlando.albertino@ufes.br";
  var DRAFT_KEY = "revista-proposta-rascunho";
  var FICHA = "revista-ficha";

  function setStatus(state, text) {
    status.dataset.state = state || "";
    status.textContent = text || "";
  }

  function slugify(texto) {
    var mapa = {
      á: "a",
      à: "a",
      ã: "a",
      â: "a",
      é: "e",
      ê: "e",
      í: "i",
      ó: "o",
      ô: "o",
      õ: "o",
      ú: "u",
      ü: "u",
      ç: "c",
    };
    return String(texto || "")
      .toLowerCase()
      .replace(/[áàãâéêíóôõúüç]/g, function (ch) {
        return mapa[ch] || ch;
      })
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function hoje() {
    return new Date().toISOString().slice(0, 10);
  }

  function escYaml(s) {
    return String(s || "")
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\n/g, " ");
  }

  function lerForm() {
    return {
      nome_completo: form.nome_completo.value.trim(),
      nome_assinatura: form.nome_assinatura.value.trim(),
      email: form.email.value.trim(),
      matricula: form.matricula.value.trim(),
      equipe: form.equipe.value,
      oficio: form.oficio.value,
      modalidade: form.modalidade.value,
      titulo: form.titulo.value.trim(),
      deck: form.deck.value.trim(),
      obras: form.obras.value.trim(),
      pergunta: form.pergunta.value.trim(),
      status_peca: form.status_peca.value,
      secao: form.secao.value,
      extensao: form.extensao.value.trim(),
      usou_ia: form.usou_ia.value,
      ia_para: form.ia_para.value.trim(),
      autoria: form.autoria.value.trim(),
      corpo: form.corpo.value.trim(),
      link_doc: form.link_doc.value.trim(),
      lgpd: form.lgpd.checked ? "sim" : "nao",
      date: hoje(),
    };
  }

  function markdown(d) {
    var secaoPasta =
      d.secao === "critica"
        ? "pecas"
        : d.secao === "indicacoes"
          ? "indicacoes"
          : "estudantina";
    var nav =
      d.secao === "critica"
        ? "critica"
        : d.secao === "indicacoes"
          ? "indicacoes"
          : "estudantina";
    var parts = d.date.split("-");
    var dataBr =
      parts.length === 3 ? parts[2] + "/" + parts[1] + "/" + parts[0] : d.date;
    var eyebrow =
      secaoPasta === "estudantina"
        ? "Em elaboração · " + dataBr
        : d.modalidade.charAt(0).toUpperCase() + d.modalidade.slice(1);
    var byline =
      d.nome_assinatura +
      (secaoPasta === "estudantina" ? " · rascunho" : "");
    var kicker =
      secaoPasta === "estudantina"
        ? "Em elaboração · " + d.modalidade
        : d.modalidade;
    var body = [
      d.corpo,
      "",
      "## Ficha enviada com a proposta",
      "",
      "- **Obras / corpus:** " + d.obras,
      "- **Pergunta crítica:** " + d.pergunta,
      "- **Status declarado:** " + d.status_peca,
      "- **Ofício:** " + d.oficio,
      "- **Extensão prevista:** " + (d.extensao || "—"),
      "- **Uso de IA:** " + d.usou_ia + (d.ia_para ? " (" + d.ia_para + ")" : ""),
      "- **Autoria crítica:** " + d.autoria,
    ];
    if (d.link_doc) {
      body.push("- **Doc anexo:** " + d.link_doc);
    }
    if (secaoPasta === "estudantina") {
      body.push(
        "",
        "Quando a peça amadurecer, sobe para [Crítica](../pecas/index.html) ou [Indicações](../indicacoes/index.html)."
      );
    }
    var linhas = [
      "---",
      'title: "' + escYaml(d.titulo) + '"',
      'eyebrow: "' + escYaml(eyebrow) + '"',
      'deck: "' + escYaml(d.deck) + '"',
      'byline: "' + escYaml(byline) + '"',
      "date: " + d.date,
      "equipe: " + d.equipe,
      'kicker: "' + escYaml(kicker) + '"',
      'resumo: "' + escYaml(d.deck) + '"',
      "nav: " + nav,
      "---",
      "",
    ].concat(body, [""]);
    return {
      secao: secaoPasta,
      slug: d.date + "-" + (slugify(d.titulo) || "proposta").slice(0, 48),
      texto: linhas.join("\n"),
    };
  }

  function preencher(d) {
    if (!d) return;
    Object.keys(d).forEach(function (key) {
      if (!form[key] || key === "lgpd" || key === "date") return;
      form[key].value = d[key] || "";
    });
  }

  function salvarLocal() {
    var d = lerForm();
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(d));
      localStorage.setItem(
        FICHA,
        JSON.stringify({
          byline: d.nome_assinatura,
          equipe: d.equipe,
          oficios: d.oficio,
          em: Date.now(),
        })
      );
      setStatus(
        "ok",
        "Rascunho guardado só neste navegador. A Editoria ainda não recebeu — use «Enviar proposta à Editoria» quando estiver pronto."
      );
    } catch (err) {
      setStatus("err", "Não foi possível guardar o rascunho neste navegador.");
    }
  }

  function baixarMd() {
    var d = lerForm();
    if (!d.titulo || !d.corpo) {
      setStatus("err", "Título e texto são obrigatórios para baixar.");
      return;
    }
    var md = markdown(d);
    var blob = new Blob([md.texto], { type: "text/markdown;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = md.slug + ".md";
    a.click();
    URL.revokeObjectURL(a.href);
    setStatus(
      "ok",
      "Cópia .md baixada no seu computador. Isso não enviou nada — para mandar à Editoria, use «Enviar proposta à Editoria»."
    );
  }

  try {
    var salvo = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null");
    if (salvo) preencher(salvo);
    else {
      var ficha = JSON.parse(localStorage.getItem(FICHA) || "null");
      if (ficha) {
        if (ficha.byline) form.nome_assinatura.value = ficha.byline;
        if (ficha.equipe) form.equipe.value = ficha.equipe;
      }
    }
  } catch (err) {
    /* ignore */
  }

  document.getElementById("salvar-local").addEventListener("click", salvarLocal);
  document.getElementById("baixar-md").addEventListener("click", baixarMd);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (form.website && form.website.value) return;
    if (!form.reportValidity()) return;

    var d = lerForm();
    var md = markdown(d);
    var payload = {
      _subject:
        "Proposta de colaboração — " +
        d.titulo +
        " — Revista Experimental (DLT13973)",
      _template: "box",
      _captcha: "false",
      _honey: form.website ? form.website.value : "",
      tipo: "proposta",
      secao_pasta: md.secao,
      arquivo: "conteudo/" + md.secao + "/" + md.slug + ".md",
      nome_completo: d.nome_completo,
      nome_assinatura: d.nome_assinatura,
      email: d.email,
      matricula: d.matricula,
      equipe: d.equipe,
      oficio: d.oficio,
      modalidade: d.modalidade,
      titulo: d.titulo,
      deck: d.deck,
      obras: d.obras,
      pergunta: d.pergunta,
      status_peca: d.status_peca,
      secao_pretendida: d.secao,
      extensao: d.extensao,
      usou_ia: d.usou_ia,
      ia_para: d.ia_para,
      autoria: d.autoria,
      link_doc: d.link_doc,
      lgpd: d.lgpd,
      markdown: md.texto,
    };

    submit.disabled = true;
    setStatus("wait", "Enviando a proposta à Editoria…");
    salvarLocal();

    fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        var data = result.data || {};
        var activated = data.success === true || data.success === "true";
        if (!result.ok || !activated) {
          if (
            String(data.message || "")
              .toLowerCase()
              .indexOf("activation") !== -1
          ) {
            throw new Error("activation");
          }
          throw new Error("Falha no envio");
        }
        setStatus(
          "ok",
          "Proposta recebida pela Editoria. Não está no ar ainda — a mesa lê e encaminha (Estudantina, Crítica ou Indicações)."
        );
      })
      .catch(function (err) {
        var mailto =
          "mailto:orlando.albertino@ufes.br?subject=" +
          encodeURIComponent("Proposta de colaboração — " + d.titulo) +
          "&body=" +
          encodeURIComponent(md.texto);
        var prefix =
          err && err.message === "activation"
            ? "O canal de e-mail da redação ainda está sendo ativado. Enquanto isso, envie pelo link — o markdown já vai no corpo."
            : "Não foi possível enviar pelo formulário. Use o e-mail da disciplina — o markdown da proposta já vai no link.";
        status.dataset.state = "err";
        status.innerHTML =
          prefix +
          ' <a href="' +
          mailto +
          '">Abrir e-mail para orlando.albertino@ufes.br</a>.';
      })
      .finally(function () {
        submit.disabled = false;
      });
  });
})();
