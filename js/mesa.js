(function () {
  var LOGIN = document.getElementById("mesa-login");
  var EDITOR = document.getElementById("mesa-editor");
  var PECA = document.getElementById("mesa-peca");
  if (!LOGIN || !EDITOR || !PECA) return;

  var SENHA =
    "fdb391df9c9b3182dd255f457b530f43ada901b0f84dc8eb9bd721a1a493f2b9";
  var SESSION = "revista-mesa-sessao";
  var FICHA = "revista-ficha";
  var ENDPOINT = "https://formsubmit.co/ajax/orlando.albertino@ufes.br";
  var COLAB_URL = "redacao/colaboradores.json";

  var loginStatus = document.getElementById("login-status");
  var pecaStatus = document.getElementById("peca-status");
  var bylineEl = document.getElementById("mesa-byline");
  var metaEl = document.getElementById("mesa-meta");
  var listaColab = document.getElementById("lista-colaboradores");
  var listaRascunhos = document.getElementById("lista-rascunhos");
  var listaImagens = document.getElementById("lista-imagens");
  var videoPreview = document.getElementById("video-preview");
  var arquivoImagem = document.getElementById("arquivo-imagem");

  var colaboradores = [];
  var rascunhoAtual = null;
  var imagens = [];

  function setStatus(el, state, text) {
    el.dataset.state = state || "";
    el.textContent = text || "";
  }

  function hex(buffer) {
    return Array.prototype.map
      .call(new Uint8Array(buffer), function (b) {
        return b.toString(16).padStart(2, "0");
      })
      .join("");
  }

  function hashSenha(texto) {
    return crypto.subtle
      .digest("SHA-256", new TextEncoder().encode(texto))
      .then(hex);
  }

  function slugify(texto) {
    var mapa = {
      á: "a", à: "a", ã: "a", â: "a", é: "e", ê: "e", í: "i",
      ó: "o", ô: "o", õ: "o", ú: "u", ü: "u", ç: "c",
    };
    return String(texto || "")
      .toLowerCase()
      .replace(/[áàãâéêíóôõúüç]/g, function (ch) {
        return mapa[ch] || ch;
      })
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function uid() {
    return "p" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function hoje() {
    return new Date().toISOString().slice(0, 10);
  }

  function youtubeId(value) {
    var raw = String(value || "").trim();
    var m = raw.match(
      /(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|shorts\/))([A-Za-z0-9_-]{11})/
    );
    if (m) return m[1];
    if (/^[A-Za-z0-9_-]{11}$/.test(raw)) return raw;
    return "";
  }

  function sessao() {
    try {
      return JSON.parse(localStorage.getItem(SESSION) || "null");
    } catch (err) {
      return null;
    }
  }

  function fichaLocal() {
    try {
      return JSON.parse(localStorage.getItem(FICHA) || "null");
    } catch (err) {
      return null;
    }
  }

  function acharColaborador(byline) {
    var chave = slugify(byline);
    var i;
    for (i = 0; i < colaboradores.length; i += 1) {
      var c = colaboradores[i];
      if (!c.ativo) continue;
      if (slugify(c.byline) === chave || slugify(c.nome) === chave || c.id === chave) {
        return c;
      }
    }
    return null;
  }

  function dbOpen() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open("revista-mesa", 1);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains("rascunhos")) {
          db.createObjectStore("rascunhos", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("imagens")) {
          db.createObjectStore("imagens", { keyPath: "id" });
        }
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
      req.onerror = function () {
        reject(req.error);
      };
    });
  }

  function dbOp(store, modo, fn) {
    return dbOpen().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(store, modo);
        var os = tx.objectStore(store);
        var req = fn(os);
        req.onsuccess = function () {
          resolve(req.result);
        };
        req.onerror = function () {
          reject(req.error);
        };
      });
    });
  }

  function listarRascunhos(byline) {
    return dbOp("rascunhos", "readonly", function (os) {
      return os.getAll();
    }).then(function (todos) {
      var chave = slugify(byline);
      return (todos || [])
        .filter(function (r) {
          return slugify(r.byline) === chave;
        })
        .sort(function (a, b) {
          return (b.atualizado || "") > (a.atualizado || "") ? 1 : -1;
        });
    });
  }

  function guardarRascunho(r) {
    return dbOp("rascunhos", "readwrite", function (os) {
      return os.put(r);
    });
  }

  function lerImagem(id) {
    return dbOp("imagens", "readonly", function (os) {
      return os.get(id);
    });
  }

  function guardarImagem(rec) {
    return dbOp("imagens", "readwrite", function (os) {
      return os.put(rec);
    });
  }

  function dadosDoForm() {
    return {
      tipo: PECA.tipo.value || "peca",
      title: PECA.title.value.trim(),
      deck: PECA.deck.value.trim(),
      byline: (sessao() || {}).byline || "",
      equipe: PECA.equipe.value,
      youtube: youtubeId(PECA.youtube.value),
      youtube_raw: PECA.youtube.value.trim(),
      body: PECA.body.value.trim(),
      date: hoje(),
      imagens: imagens.slice(),
    };
  }

  function preencherForm(r) {
    PECA.tipo.value = r.tipo || "peca";
    PECA.title.value = r.title || "";
    PECA.deck.value = r.deck || "";
    if (r.equipe) PECA.equipe.value = r.equipe;
    PECA.youtube.value = r.youtube_raw || r.youtube || "";
    PECA.body.value = r.body || "";
    imagens = r.imagens || [];
    rascunhoAtual = r.id;
    pintarVideo();
    pintarImagens();
  }

  function formularioVazio() {
    var s = sessao() || {};
    var ficha = fichaLocal() || {};
    preencherForm({
      id: uid(),
      tipo: "estudantina",
      title: "",
      deck: "",
      equipe: ficha.equipe || s.equipe || "",
      youtube: "",
      youtube_raw: "",
      body: "",
      imagens: [],
    });
    setStatus(pecaStatus, "", "");
  }

  function markdown(d) {
    var secao =
      d.tipo === "indicacao"
        ? "indicacoes"
        : d.tipo === "estudantina"
          ? "estudantina"
          : "pecas";
    var nav =
      d.tipo === "indicacao"
        ? "indicacoes"
        : d.tipo === "estudantina"
          ? "estudantina"
          : "critica";
    var eyebrow =
      d.tipo === "indicacao"
        ? "Indicação"
        : d.tipo === "estudantina"
          ? "Em elaboração"
          : "Crítica";
    var byline =
      d.tipo === "estudantina" && d.byline.indexOf("rascunho") === -1
        ? d.byline + " · rascunho"
        : d.byline;
    var linhas = [
      "---",
      'title: "' + d.title.replace(/"/g, '\\"') + '"',
      'eyebrow: "' + eyebrow + '"',
      'deck: "' + d.deck.replace(/"/g, '\\"') + '"',
      'byline: "' + byline.replace(/"/g, '\\"') + '"',
      "date: " + d.date,
      "equipe: " + d.equipe,
      "nav: " + nav,
    ];
    if (d.tipo === "estudantina") {
      linhas.push('kicker: "Em elaboração"');
      linhas.push('resumo: "' + d.deck.replace(/"/g, '\\"') + '"');
    }
    if (d.youtube) {
      linhas.push("youtube: " + d.youtube);
      linhas.push('origem: "https://youtu.be/' + d.youtube + '"');
    }
    linhas.push("---", "", d.body, "");
    return {
      secao: secao,
      slug: d.date + "-" + (slugify(d.title) || "peca").slice(0, 48),
      texto: linhas.join("\n"),
    };
  }

  function insertAtCursor(textarea, text) {
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    textarea.value =
      textarea.value.slice(0, start) + text + textarea.value.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    textarea.focus();
  }

  function pintarVideo() {
    var id = youtubeId(PECA.youtube.value);
    if (!id) {
      videoPreview.hidden = true;
      videoPreview.innerHTML = "";
      return;
    }
    videoPreview.hidden = false;
    videoPreview.innerHTML =
      '<figure class="video-frame"><iframe src="https://www.youtube-nocookie.com/embed/' +
      id +
      '" title="Prévia do vídeo" allow="encrypted-media; picture-in-picture" allowfullscreen loading="lazy"></iframe></figure>';
  }

  function pintarImagens() {
    listaImagens.innerHTML = "";
    if (!imagens.length) {
      listaImagens.innerHTML = "<li>Nenhuma imagem neste rascunho.</li>";
      return;
    }
    imagens.forEach(function (img) {
      var li = document.createElement("li");
      li.textContent = img.name + " — " + (img.alt || "sem legenda");
      listaImagens.appendChild(li);
    });
  }

  function pintarLista(byline) {
    return listarRascunhos(byline)
      .then(function (lista) {
        listaRascunhos.innerHTML = "";
        if (!lista.length) {
          listaRascunhos.innerHTML = "<li>Nenhum rascunho ainda.</li>";
          return;
        }
        lista.forEach(function (r) {
          var li = document.createElement("li");
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "linkish";
          btn.textContent =
            (r.title || "Sem título") +
            (r.status === "enviado" ? " · enviado" : "");
          btn.addEventListener("click", function () {
            preencherForm(r);
          });
          li.appendChild(btn);
          listaRascunhos.appendChild(li);
        });
      })
      .catch(function () {
        listaRascunhos.innerHTML = "<li>Não foi possível ler os rascunhos deste navegador.</li>";
      });
  }

  function salvarAgora(status) {
    var d = dadosDoForm();
    var r = {
      id: rascunhoAtual || uid(),
      atualizado: new Date().toISOString(),
      status: status || "rascunho",
      tipo: d.tipo,
      title: d.title,
      deck: d.deck,
      byline: d.byline,
      equipe: d.equipe,
      youtube: d.youtube,
      youtube_raw: d.youtube_raw,
      body: d.body,
      imagens: d.imagens,
    };
    rascunhoAtual = r.id;
    return guardarRascunho(r).then(function () {
      return pintarLista(d.byline);
    });
  }

  function abrirEditor(colab, byline) {
    LOGIN.hidden = true;
    EDITOR.hidden = false;
    bylineEl.textContent = byline;
    metaEl.textContent = (colab && colab.equipe) || "equipe a registrar";
    if (colab && colab.equipe && !PECA.equipe.value) PECA.equipe.value = colab.equipe;
    formularioVazio();
    pintarLista(byline);
  }

  fetch(COLAB_URL)
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      colaboradores = data.colaboradores || [];
      if (!listaColab) return;
      listaColab.innerHTML = "";
      colaboradores
        .filter(function (c) {
          return c.ativo && c.id !== "orlando-lopes";
        })
        .forEach(function (c) {
          var li = document.createElement("li");
          li.textContent = c.byline;
          listaColab.appendChild(li);
        });
    })
    .catch(function () {
      if (listaColab) {
        listaColab.innerHTML = "<li>Não foi possível carregar o cadastro agora.</li>";
      }
    });

  var atual = sessao();
  if (atual && atual.byline) {
    fetch(COLAB_URL)
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        colaboradores = data.colaboradores || [];
        var colab = acharColaborador(atual.byline);
        if (colab || fichaLocal()) abrirEditor(colab, atual.byline);
      });
  }

  LOGIN.addEventListener("submit", function (event) {
    event.preventDefault();
    var byline = LOGIN.login_assinatura.value.trim();
    var senha = LOGIN.login_senha.value;
    if (!byline || !senha) return;
    hashSenha(senha)
      .then(function (digest) {
        if (digest !== SENHA) {
          setStatus(loginStatus, "err", "Senha da redação não confere.");
          return;
        }
        var colab = acharColaborador(byline);
        var ficha = fichaLocal();
        var fichaBate = ficha && slugify(ficha.byline) === slugify(byline);
        if (!colab && !fichaBate) {
          setStatus(
            loginStatus,
            "err",
            "Este byline ainda não está no cadastro da redação. Preencha a ficha editorial primeiro."
          );
          return;
        }
        localStorage.setItem(
          SESSION,
          JSON.stringify({
            byline: (colab && colab.byline) || byline,
            equipe: (colab && colab.equipe) || (ficha && ficha.equipe) || "",
            em: Date.now(),
          })
        );
        setStatus(loginStatus, "", "");
        abrirEditor(colab, (colab && colab.byline) || byline);
      })
      .catch(function () {
        setStatus(
          loginStatus,
          "err",
          "Este navegador não consegue abrir a mesa. Tente outro, ou o e-mail da disciplina."
        );
      });
  });

  document.getElementById("sair").addEventListener("click", function () {
    localStorage.removeItem(SESSION);
    EDITOR.hidden = true;
    LOGIN.hidden = false;
    LOGIN.login_senha.value = "";
    LOGIN.login_assinatura.focus();
  });

  document.getElementById("novo-rascunho").addEventListener("click", formularioVazio);

  document.getElementById("salvar-rascunho").addEventListener("click", function () {
    salvarAgora("rascunho")
      .then(function () {
        setStatus(pecaStatus, "ok", "Rascunho salvo neste navegador.");
      })
      .catch(function () {
        setStatus(pecaStatus, "err", "Não foi possível salvar o rascunho.");
      });
  });

  PECA.addEventListener("input", function () {
    pintarVideo();
    window.clearTimeout(PECA._saveTimer);
    PECA._saveTimer = window.setTimeout(function () {
      salvarAgora("rascunho").catch(function () {
        /* autosave silencioso */
      });
    }, 450);
  });
  PECA.youtube.addEventListener("change", pintarVideo);

  document.getElementById("inserir-video").addEventListener("click", function () {
    var bruto = window.prompt("Cole o endereço do YouTube ou o ID do vídeo:");
    if (!bruto) return;
    var id = youtubeId(bruto);
    if (!id) {
      setStatus(pecaStatus, "err", "Não reconheci esse endereço de vídeo.");
      return;
    }
    PECA.youtube.value = bruto.trim();
    insertAtCursor(PECA.body, "\n\nhttps://youtu.be/" + id + "\n\n");
    pintarVideo();
    PECA.dispatchEvent(new Event("input"));
  });

  document.getElementById("inserir-imagem").addEventListener("click", function () {
    arquivoImagem.click();
  });

  arquivoImagem.addEventListener("change", function () {
    var file = arquivoImagem.files && arquivoImagem.files[0];
    arquivoImagem.value = "";
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      setStatus(pecaStatus, "err", "Imagem acima de 4 MB. Reduza antes de inserir.");
      return;
    }
    var alt = window.prompt("Legenda da imagem (vai no texto e no crédito):", "") || "";
    var rec = {
      id: uid(),
      name: file.name,
      mime: file.type || "image/jpeg",
      alt: alt,
      blob: file,
    };
    guardarImagem(rec)
      .then(function () {
        imagens.push({
          id: rec.id,
          name: rec.name,
          mime: rec.mime,
          alt: rec.alt,
        });
        insertAtCursor(
          PECA.body,
          "\n\n![" + (alt || rec.name) + "](img/uploads/" + rec.id + "-" + rec.name.replace(/\s+/g, "-") + ")\n\n"
        );
        pintarImagens();
        return salvarAgora("rascunho");
      })
      .catch(function () {
        setStatus(pecaStatus, "err", "Não foi possível guardar a imagem neste navegador.");
      });
  });

  document.getElementById("baixar-md").addEventListener("click", function () {
    var d = dadosDoForm();
    if (!d.title || !d.body) {
      setStatus(pecaStatus, "err", "Título e texto são obrigatórios para baixar.");
      return;
    }
    var md = markdown(d);
    var blob = new Blob([md.texto], { type: "text/markdown;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = md.slug + ".md";
    a.click();
    URL.revokeObjectURL(a.href);
    setStatus(pecaStatus, "ok", "Markdown baixado. As imagens deste rascunho precisam ir à parte, no envio.");
  });

  PECA.addEventListener("submit", function (event) {
    event.preventDefault();
    if (PECA.website && PECA.website.value) return;
    var d = dadosDoForm();
    if (!d.title || !d.body) return;
    var md = markdown(d);
    var enviar = document.getElementById("enviar-peca");
    enviar.disabled = true;
    setStatus(pecaStatus, "wait", "Enviando à redação…");

    var jobs = (d.imagens || []).map(function (img) {
      return lerImagem(img.id);
    });

    Promise.all(jobs)
      .then(function (arquivos) {
        var fd = new FormData();
        fd.append(
          "_subject",
          (d.tipo === "indicacao"
            ? "Indicação"
            : d.tipo === "estudantina"
              ? "Proposta / Estudantina"
              : "Peça") +
            " — " +
            d.title +
            " — Revista Experimental (DLT13973)"
        );
        fd.append("_template", "box");
        fd.append("_captcha", "false");
        fd.append("tipo", d.tipo);
        fd.append("title", d.title);
        fd.append("deck", d.deck);
        fd.append("byline", d.byline);
        fd.append("equipe", d.equipe);
        fd.append("youtube", d.youtube);
        fd.append("arquivo", md.secao + "/" + md.slug + ".md");
        fd.append("markdown", md.texto);
        (arquivos || []).forEach(function (rec, i) {
          if (rec && rec.blob) {
            fd.append("imagem_" + (i + 1), rec.blob, rec.name);
          }
        });
        return fetch(ENDPOINT, {
          method: "POST",
          headers: { Accept: "application/json" },
          body: fd,
        }).then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        });
      })
      .then(function (result) {
        var data = result.data || {};
        var activated = data.success === true || data.success === "true";
        if (!result.ok || !activated) {
          if (String(data.message || "").toLowerCase().indexOf("activation") !== -1) {
            throw new Error("activation");
          }
          throw new Error("Falha no envio");
        }
        return salvarAgora("enviado").then(function () {
          setStatus(
            pecaStatus,
            "ok",
            "Chegou à redação, com o markdown e as imagens. O texto só entra no ar depois do editor aceitar."
          );
        });
      })
      .catch(function (err) {
        var mailto =
          "mailto:orlando.albertino@ufes.br?subject=" +
          encodeURIComponent(
            (d.tipo === "indicacao"
              ? "Indicação"
              : d.tipo === "estudantina"
                ? "Proposta / Estudantina"
                : "Peça") +
              " — " +
              d.title
          ) +
          "&body=" +
          encodeURIComponent(md.texto);
        var prefix =
          err && err.message === "activation"
            ? "O canal de e-mail ainda está sendo ativado. Enquanto isso, envie pelo link. As imagens ficam no rascunho deste navegador."
            : "Não foi possível enviar pelo formulário. Use o e-mail da disciplina — o markdown já vai no link. Anexe as imagens se houver.";
        pecaStatus.dataset.state = "err";
        pecaStatus.innerHTML =
          prefix +
          ' <a href="' +
          mailto +
          '">Abrir e-mail para orlando.albertino@ufes.br</a>.';
      })
      .finally(function () {
        enviar.disabled = false;
      });
  });
})();
