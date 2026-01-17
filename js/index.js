lucide.createIcons();

// VARIABLES GLOBALES (Compartidas por ambos generadores)
let allData = [];
let sortedData = [];
let pastCombinations = new Set();
let currentGeneratedNumbers = []; // IMPORTANTE: Aqui se guardan los numeros antes de enviarlos

const PRIMOS_LOTO = new Set([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]);

function formatMoney(n) { return '$' + Number(n).toLocaleString('es-CL'); }

// =========================================
// 1. CARGA DE DATOS CSV
// =========================================
try {
  Papa.parse('data/LOTO_HISTORIAL_MAESTRO.csv', {
    download: true, header: true, skipEmptyLines: true,
    complete: function(results) {
      allData = results.data;

      allData.forEach(row => {
          if(row.LOTO_n1 && row.LOTO_n6) {
              let nums = [
                  parseInt(row.LOTO_n1), parseInt(row.LOTO_n2), parseInt(row.LOTO_n3),
                  parseInt(row.LOTO_n4), parseInt(row.LOTO_n5), parseInt(row.LOTO_n6)
              ];
              nums.sort((a,b) => a-b);
              pastCombinations.add(nums.join('-'));
          }
      });

      const validData = allData.filter(row => row.sorteo && row.sorteo.trim() !== '');
      const lastDraw = validData[validData.length - 1];

      if(lastDraw) {
         renderDashboard(lastDraw);
         const searchInput = document.getElementById('search');
         if(searchInput) searchInput.max = lastDraw.sorteo;
      }

      sortedData = validData.slice().reverse();
      updateHistoryTable();

      const statusText = document.getElementById('status-text');
      if(statusText) statusText.style.display = 'none';
    }
  });
} catch(e) {
  console.error("Error inicial:", e);
  document.getElementById('status-text').textContent = "Error al iniciar la carga de datos.";
}

// =========================================
// 1.5 CARGA DE METRICAS REALES (SIMULACIONES)
// =========================================
function loadRealMetrics() {
    Papa.parse('data/LOTO_SIMULACIONES.csv', {
        download: true, header: true, skipEmptyLines: true,
        complete: function(results) {
            const simData = results.data;

            // Filtrar solo predicciones AUDITADAS de LOTO
            const auditedLoto = simData.filter(row =>
                row.estado === 'AUDITADO' && row.juego === 'LOTO'
            );

            if (auditedLoto.length === 0) {
                document.getElementById('total-predictions').textContent = '0';
                document.getElementById('avg-loto-hits').textContent = 'N/A';
                document.getElementById('best-loto-hits').textContent = 'N/A';
                document.getElementById('success-rate').textContent = 'N/A';
                return;
            }

            // Calcular metricas
            const totalPredictions = simData.filter(r => r.estado === 'AUDITADO').length;
            const lotoHits = auditedLoto.map(r => parseInt(r.aciertos) || 0);
            const avgHits = lotoHits.reduce((a, b) => a + b, 0) / lotoHits.length;
            const maxHits = Math.max(...lotoHits);
            const successCount = lotoHits.filter(h => h >= 3).length;
            const successRate = (successCount / lotoHits.length) * 100;

            // Actualizar UI
            document.getElementById('total-predictions').textContent = totalPredictions.toLocaleString();
            document.getElementById('avg-loto-hits').textContent = avgHits.toFixed(2);
            document.getElementById('best-loto-hits').textContent = maxHits + '/6';
            document.getElementById('success-rate').textContent = successRate.toFixed(1) + '%';

            // Color coding based on performance
            const avgEl = document.getElementById('avg-loto-hits');
            if (avgHits < 1.0) {
                avgEl.classList.add('metric-bad');
            } else if (avgHits < 2.0) {
                avgEl.classList.add('metric-neutral');
            } else {
                avgEl.classList.add('metric-info');
            }

            console.log('Metricas reales cargadas:', {
                total: totalPredictions,
                lotoAuditados: auditedLoto.length,
                promedioAciertos: avgHits.toFixed(2),
                maxAciertos: maxHits,
                tasaExito: successRate.toFixed(1) + '%'
            });
        },
        error: function(err) {
            console.warn('No se pudo cargar SIMULACIONES:', err);
            // Mostrar N/A si no se puede cargar
            document.getElementById('total-predictions').textContent = 'N/A';
            document.getElementById('avg-loto-hits').textContent = 'N/A';
            document.getElementById('best-loto-hits').textContent = 'N/A';
            document.getElementById('success-rate').textContent = 'N/A';
        }
    });
}

// Cargar metricas al iniciar
loadRealMetrics();

// =========================================
// 2. LOGICA DEL GENERADOR CUANTICO (MODIFICADO CON PESO MECANICO)
// =========================================
function generateLuckyNumbers() {
    const output = document.getElementById('gen-output');
    const container = document.getElementById('gen-balls-container');
    const telemetry = document.getElementById('telemetry-panel');
    const stats = document.getElementById('gen-stats-text');

    output.style.display = 'block'; output.style.opacity = '1';
    container.innerHTML = '<div style="color:var(--gold);">Simulando extraccion fisica...</div>';
    telemetry.innerHTML = ''; stats.innerHTML = '';
    const oldActions = document.getElementById('gen-actions'); if(oldActions) oldActions.remove();

    setTimeout(() => {
        let attempt = 0, success = false, finalNums = [];

        while(attempt < 5000) {
            attempt++;
            let candidates = new Set();

            // --- NUEVA LOGICA: SELECCION POR TORNEO POSICIONAL ---
            // Simulamos la salida de la bola 1, luego la 2, hasta la 6
            for (let pos = 1; pos <= 6; pos++) {
                let bestCandidate = null;
                let maxScore = -1;

                // Probamos 5 candidatos al azar para esta posicion
                for (let k = 0; k < 5; k++) {
                    let testNum = Math.floor(Math.random() * 41) + 1;

                    // Si ya salio en esta jugada, lo ignoramos
                    if (candidates.has(testNum)) continue;

                    // Calculamos su "afinidad" por esta posicion especifica
                    let weight = getMechanicalWeight(testNum, pos, allData);

                    // Factor aleatorio para mantener la variabilidad
                    let score = weight * Math.random();

                    if (score > maxScore) {
                        maxScore = score;
                        bestCandidate = testNum;
                    }
                }

                // Si encontramos candidato, lo agregamos. Si no (mala suerte), azar puro.
                if (bestCandidate && !candidates.has(bestCandidate)) {
                    candidates.add(bestCandidate);
                } else {
                    let r = Math.floor(Math.random() * 41) + 1;
                    while(candidates.has(r)) r = Math.floor(Math.random() * 41) + 1;
                    candidates.add(r);
                }
            }
            // -----------------------------------------------------

            let nums = Array.from(candidates).sort((a,b) => a-b);

            // Filtros estandar (Suma, Paridad, Inedita, Consecutivos)
            let sum = nums.reduce((a,b) => a+b, 0); if(sum < 100 || sum > 150) continue;
            let evens = nums.filter(n => n % 2 === 0).length; if(evens < 2 || evens > 4) continue;
            if(pastCombinations.has(nums.join('-'))) continue;
            let maxCons = 0, cons = 0;
            for(let i=0; i<nums.length-1; i++) { if(nums[i+1] === nums[i]+1) cons++; else cons = 0; if(cons > maxCons) maxCons = cons; }
            if(maxCons >= 2) continue;

            finalNums = nums; success = true; break;
        }

        if(success) {
            currentGeneratedNumbers = finalNums;
            container.innerHTML = finalNums.map(n => `<div class="gen-ball">${n}</div>`).join('');

            let sum = finalNums.reduce((a,b) => a+b, 0);
            let evens = finalNums.filter(n => n % 2 === 0).length;
            let range = finalNums[finalNums.length-1] - finalNums[0];
            let primesCount = finalNums.filter(n => PRIMOS_LOTO.has(n)).length;
            let decades = new Set(finalNums.map(n => Math.floor(n/10))).size;
            let consecutivesCount = 0;
            for(let i=0; i<finalNums.length-1; i++) if(finalNums[i+1] === finalNums[i]+1) consecutivesCount++;

            let rangeClass = (range >= 20 && range <= 38) ? 'metric-good' : 'metric-warn';
            let primeClass = (primesCount >= 1 && primesCount <= 3) ? 'metric-good' : 'metric-warn';
            let zoneClass = (decades >= 3) ? 'metric-good' : 'metric-warn';
            let consClass = (consecutivesCount === 0) ? 'metric-good' : 'metric-warn';

            // --- TEXTOS EXPLICATIVOS PARA TOOLTIPS ---
            const rangeTip = `RANGO: La resta entre el numero mayor y el menor es ${range}. Lo ideal es entre 20 y 38 para cubrir bien el carton.`;
            const primeTip = `PRIMOS: Hay ${primesCount} numeros primos. La estadistica sugiere jugar entre 1 y 3 primos por sorteo.`;
            const zoneTip = `ZONAS: Tus numeros cubren ${decades} decenas diferentes. Lo ideal es no concentrar todo en una sola decena.`;
            const consTip = `CONSECUTIVOS: Tienes ${consecutivesCount} numeros seguidos. Es mejor tener 0 o maximo 1 par consecutivo.`;

            telemetry.innerHTML = `
                <div class="tele-item" data-title="${rangeTip}"><span class="tele-label">Rango (20-38)</span><span class="tele-val ${rangeClass}"><i data-lucide="ruler" width="14"></i> ${range}</span></div>
                <div class="tele-item" data-title="${primeTip}"><span class="tele-label">Primos (1-3)</span><span class="tele-val ${primeClass}"><i data-lucide="hash" width="14"></i> ${primesCount}</span></div>
                <div class="tele-item" data-title="${zoneTip}"><span class="tele-label">Zonas (>3)</span><span class="tele-val ${zoneClass}"><i data-lucide="map" width="14"></i> ${decades}</span></div>
                <div class="tele-item" data-title="${consTip}"><span class="tele-label">Consecutivos</span><span class="tele-val ${consClass}"><i data-lucide="link" width="14"></i> ${consecutivesCount}</span></div>
            `;
            stats.innerHTML = `Suma: ${sum} | Paridad: ${evens}P-${6-evens}I | Inedita`;

            const actionsDiv = document.createElement('div');
            actionsDiv.id = 'gen-actions';
            actionsDiv.style.marginTop = '1.5rem'; actionsDiv.style.display = 'flex'; actionsDiv.style.justifyContent = 'center'; actionsDiv.style.gap = '15px';
            actionsDiv.innerHTML = `
                <button onclick="savePlay(true)" class="gen-btn" style="font-size:0.8rem; padding:0.8rem 1.5rem; background:#00ff41; color:black; border:none; box-shadow:0 0 15px rgba(0,255,65,0.3);"><i data-lucide="ticket" style="width:16px; margin-right:5px;"></i> LA JUGUE!</button>
                <button onclick="savePlay(false)" class="gen-btn" style="font-size:0.8rem; padding:0.8rem 1.5rem; background:transparent; border:1px solid #a0aec0; color:#a0aec0; box-shadow:none;"><i data-lucide="save" style="width:16px; margin-right:5px;"></i> Solo Guardar</button>`;
            output.appendChild(actionsDiv);
            lucide.createIcons();
        } else container.innerHTML = "Error de convergencia.";
    }, 400);
}

async function savePlay(playedReal) {
    if(currentGeneratedNumbers.length === 0) return;

    // MODIFICACION: Buscar contenedor del panel dorado O el panel forense
    let btnContainer = document.getElementById('gen-actions');
    if(!btnContainer || btnContainer.offsetParent === null) {
        btnContainer = document.getElementById('gen-actions-forensic');
    }

    if(btnContainer) btnContainer.innerHTML = '<span style="color:var(--neon-cyan);">Sincronizando...</span>';
    const GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwBZd2vTrvxVdTjJnLoK2vMCR90qJqyH3ZfSDkNK4_n0aFYe3jCoeIZ3R58XNQBM1xQ3A/exec";
    try {
        await fetch(GOOGLE_SCRIPT_URL, {
            method: 'POST', mode: 'no-cors', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ numeros: currentGeneratedNumbers, jugado: playedReal ? "SI" : "NO" })
        });
        if(btnContainer) {
            btnContainer.innerHTML = '<span style="color:#00ff41; font-weight:bold;">Guardado!</span>';
            setTimeout(() => { btnContainer.style.opacity = '0'; }, 3000);
        }
    } catch (error) {
        if(btnContainer) btnContainer.innerHTML = '<span style="color:red;">Error de conexion.</span>';
    }
}

// =========================================
// 3. RENDERIZADO DEL DASHBOARD
// =========================================
function renderDashboard(row) {
  // A. CALCULO TOTAL REPARTIDO
  let totalRepartido = 0;
  let totalGanadores = 0;

  Object.keys(row).forEach(key => {
    if (key.endsWith('_GANADORES')) {
      const winners = parseInt(row[key]) || 0;
      if (winners > 0) {
        totalGanadores += winners;
        const prefix = key.replace('_GANADORES', '');
        const amountKey = prefix + '_MONTO';
        const amount = parseInt(row[amountKey]) || 0;
        totalRepartido += amount;
      }
    }
  });

  const elDate = document.getElementById('dash-date');
  const elTitle = document.getElementById('dash-title');
  const elMoney = document.getElementById('dash-money');
  const elWinners = document.getElementById('dash-winners');

  if(elDate) elDate.innerText = row.fecha ? row.fecha.split(' ')[0] : '---';
  if(elTitle) elTitle.innerText = `Sorteo #${row.sorteo}`;
  if(elMoney) elMoney.innerText = formatMoney(totalRepartido);
  if(elWinners) elWinners.innerText = totalGanadores.toLocaleString('es-CL');

  // B. RENDERIZADO DE SWIPER (BOLITAS)
  const gamesConfig = [
    { key: 'LOTO', title: 'LOTO CLASICO', color: '#facc15' },
    { key: 'RECARGADO', title: 'RECARGADO', color: '#fbbf24' },
    { key: 'REVANCHA', title: 'REVANCHA', color: '#f87171' },
    { key: 'DESQUITE', title: 'DESQUITE', color: '#34d399' },
    { key: 'AHORA_SI_QUE_SI', title: 'AHORA SI QUE SI', color: '#22d3ee' }
  ];

  const swiperWrapper = document.getElementById('games-container');
  let slidesHtml = '';

  gamesConfig.forEach(game => {
    const n1 = row[`${game.key}_n1`];
    if (!n1 || n1.toString().trim() === '') return;

    let numbers = [];
    for(let i=1; i<=6; i++) {
       const val = row[`${game.key}_n${i}`];
       if(val) numbers.push(parseInt(val));
    }
    numbers.sort((a, b) => a - b);

    let ballsHtml = numbers.map(num => `<div class="ball ${game.key}">${num}</div>`).join('');
    const comodin = row[`${game.key}_comodin`];
    const hasComodin = (comodin && comodin.toString().trim() !== '' && comodin != '0');
    const comodinHtml = hasComodin ? `<div class="ball COMODIN" title="Comodin">${comodin}</div>` : '';
    const ganadores = parseInt(row[`${game.key}_GANADORES`]) || 0;
    const monto = parseInt(row[`${game.key}_MONTO`]) || 0;

    let footerHtml = ganadores > 0 ?
        `<div style="margin-top:auto; padding-top:1rem; border-top: 1px solid rgba(74, 222, 128, 0.3);">
          <div style="background: rgba(20, 83, 45, 0.4); border: 1px solid rgba(74, 222, 128, 0.4); border-radius: 12px; padding: 10px; text-align: center;">
             <div style="color:#4ade80; font-size:0.75rem; font-weight:bold;">${ganadores} Ganador(es)!</div>
             <div style="font-size:1.1rem; font-weight:900; color:white; font-family:monospace;">${formatMoney(monto)}</div>
          </div></div>` :
        `<div style="margin-top:auto; padding-top:1rem; border-top: 1px solid rgba(255,255,255,0.05);">
          <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 10px; text-align: center;">
             <div style="font-size:0.75rem; color:#6b7280; font-weight:600;">Pozo Estimado</div>
             <div style="font-size:1.1rem; font-weight:bold; color:rgba(255,255,255,0.8);">VACANTE</div>
          </div></div>`;

    slidesHtml += `
      <div class="swiper-slide" style="height: auto; padding: 5px;">
        <div style="display: flex; flex-direction: column; height: 100%; background: #0f1525; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 1.5rem;">
          <div style="text-align: center; margin-bottom: 1.5rem;"><h3 style="font-size: 1.5rem; font-weight: 900; font-style: italic; color: ${game.color};">${game.title}</h3></div>
          <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 1.5rem;">
            <div style="display: grid; grid-template-columns: auto auto; gap: 12px;">${ballsHtml}</div>
            ${hasComodin ? `<div style="display: flex; justify-content: center; margin-top: 15px; padding-top: 15px; border-top: 1px dashed rgba(255,255,255,0.1); width: 60%;">${comodinHtml}</div>` : ''}
          </div>
          ${footerHtml}
        </div>
      </div>`;
  });

  swiperWrapper.innerHTML = slidesHtml;
  if(window.mySwiper) { window.mySwiper.update(); window.mySwiper.slideTo(0); }
  else { window.mySwiper = new Swiper('.swiper', { slidesPerView: 1, spaceBetween: 20, centeredSlides: false, pagination: { el: '.swiper-pagination', clickable: true }, breakpoints: { 640: { slidesPerView: 1.2, centeredSlides: true }, 768: { slidesPerView: 2 }, 1024: { slidesPerView: 3 } } }); }

  // C. RENDERIZADO DEL DESGLOSE DETALLADO
  const categories = [
        { key: 'LOTO', label: 'Loto 6 Aciertos', type: 'jackpot' },
        { key: 'RECARGADO_6_ACIERTOS', label: 'Recargado', type: 'jackpot' },
        { key: 'REVANCHA', label: 'Revancha', type: 'jackpot' },
        { key: 'DESQUITE', label: 'Desquite', type: 'jackpot' },
        { key: 'AHORA_SI_QUE_SI', label: 'Ahora Si que Si', type: 'jackpot' },
        { key: 'SUPER_QUINA_5_ACIERTOS_COMODIN', label: 'S. Quina + Comodin', type: 'secondary' },
        { key: 'QUINA_5_ACIERTOS', label: 'Quina', type: 'secondary' },
        { key: 'SUPER_CUATERNA_4_ACIERTOS_COMODIN', label: 'S. Cuaterna + Comodin', type: 'secondary' },
        { key: 'CUATERNA_4_ACIERTOS', label: 'Cuaterna', type: 'secondary' },
        { key: 'SUPER_TERNA_3_ACIERTOS_COMODIN', label: 'S. Terna + Comodin', type: 'secondary' },
        { key: 'TERNA_3_ACIERTOS', label: 'Terna', type: 'secondary' },
        { key: 'SUPER_DUPLA_2_ACIERTOS_COMODIN', label: 'S. Dupla + Comodin', type: 'secondary' }
  ];

  let breakdownHtml = '';
  categories.forEach(cat => {
        const winnersCol = `${cat.key}_GANADORES`;
        const amountCol = `${cat.key}_MONTO`;

        const winners = parseInt(row[winnersCol]) || 0;
        let amountTotal = parseInt(row[amountCol]) || 0;

        let displayAmount = amountTotal;
        let isVacante = winners === 0;

        if (isVacante) {
            // LOGICA CORREGIDA: Prioridad al POZO ACUMULADO (Garantizado) sobre el REAL (Ventas)
            let pozoCol = null;

            // 1. Definimos las posibles columnas donde se esconde el "Acumulado", en orden de prioridad
            const candidates = [
                `${cat.key}_POZO_ACUMULADO`,  // Estandar (Loto, Revancha, Desquite)
                `${cat.key}_ACUMULADO`,       // A veces usado en Ahora Si Que Si
                // Parche especifico para Recargado (cuya key es RECARGADO_6_ACIERTOS pero su pozo suele ser RECARGADO_POZO_ACUMULADO)
                cat.key.includes('RECARGADO') ? 'RECARGADO_POZO_ACUMULADO' : null
            ];

            // 2. Buscamos la primera columna que exista en el CSV
            for (const col of candidates) {
                if (col && col in row) {
                    pozoCol = col;
                    break;
                }
            }

            // 3. Fallback: Solo si no hay acumulado, mostramos el Real (mejor que $0)
            if (!pozoCol && `${cat.key}_POZO_REAL` in row) {
                pozoCol = `${cat.key}_POZO_REAL`;
            }

            if (pozoCol) displayAmount = parseInt(row[pozoCol]) || 0;
        }

        let prizePerPerson = winners > 0 ? amountTotal / winners : 0;

        breakdownHtml += `
            <div class="prize-card ${cat.type === 'jackpot' ? 'jackpot' : ''}">
                <div class="prize-title">${cat.label}</div>
                <div class="prize-winners">
                    ${isVacante
                        ? `<span class="vacante-tag">VACANTE</span>`
                        : `<i data-lucide="users" width="18"></i> ${winners.toLocaleString('es-CL')}`
                    }
                </div>
                <div class="prize-amount">
                    ${isVacante ? 'Pozo Estimado: ' : 'Total Repartido: '} ${formatMoney(displayAmount)}
                </div>
                ${!isVacante ? `
                    <div class="individual-prize">
                        <span>c/u:</span>
                        <span style="color:var(--neon-cyan)">${formatMoney(prizePerPerson)}</span>
                    </div>
                ` : ''}
            </div>
        `;
  });

  document.getElementById('prizes-breakdown').innerHTML = `
        <div class="breakdown-container">
            <div class="breakdown-header">
                <h3 style="color:white; font-size:1.2rem;">Detalle Financiero</h3>
                <div class="total-repartido-badge">Repartido Real: ${formatMoney(totalRepartido)}</div>
            </div>
            <div class="prize-grid">
                ${breakdownHtml}
            </div>
        </div>
  `;
  lucide.createIcons();
}

// =========================================
// 4. TABLA DE HISTORIAL
// =========================================
function updateHistoryTable() {
  const checkbox = document.getElementById('filter-winners');
  const showWinnersOnly = checkbox ? checkbox.checked : false;
  let dataToRender = sortedData;
  if (showWinnersOnly) dataToRender = sortedData.filter(r => parseInt(r.LOTO_GANADORES) > 0);
  renderHistory(dataToRender.slice(0, 100));
}

function renderHistory(rows) {
  const tbody = document.getElementById('history-body');
  tbody.innerHTML = rows.map(r => {
    let nums = [];
    for(let i=1; i<=6; i++) { if(r[`LOTO_n${i}`]) nums.push(parseInt(r[`LOTO_n${i}`])); }
    nums.sort((a, b) => a - b);
    const winner = (parseInt(r.LOTO_GANADORES) > 0);
    return `<tr style="cursor:pointer;" onclick="loadDraw('${r.sorteo}')" class="hover:bg-white/5 transition">
        <td style="padding:1rem; color:#00f2ff; font-weight:bold;">#${r.sorteo}</td>
        <td style="padding:1rem; color:#a0aec0;">${r.fecha ? r.fecha.split(' ')[0] : '-'}</td>
        <td style="padding:1rem; color:white; font-family:monospace; font-size:1.1rem;">${nums.join(' - ')} ${r.LOTO_comodin ? `<span style="color:#ff3b5c; margin-left:8px;">+ ${r.LOTO_comodin}</span>` : ''}</td>
        <td style="padding:1rem;">${winner ? '<span style="background:rgba(0,255,157,0.2); color:#00ff9d; padding:4px 8px; border-radius:99px; font-size:0.8rem; font-weight:bold;">GANADOR</span>' : '<span style="color:#718096; font-size:0.9rem;">Vacante</span>'}</td>
      </tr>`;
  }).join('');
}

document.getElementById('search').addEventListener('change', (e) => loadDraw(e.target.value));
document.getElementById('filter-winners').addEventListener('change', updateHistoryTable);
window.loadDraw = (id) => { const row = allData.find(r => r.sorteo == id); if(row) { renderDashboard(row); document.getElementById('dashboard').scrollIntoView({behavior: 'smooth'}); } }

// =========================================
// 5. INICIALIZACION DEL TEMPORIZADOR
// =========================================
function initTimer() {
  const update = () => {
    const now = new Date(); let next = new Date(); next.setHours(21, 0, 0, 0);
    while(![0,2,4].includes(next.getDay()) || next < now) { next.setDate(next.getDate() + 1); next.setHours(21, 0, 0, 0); }
    const diff = next - now;
    const d = Math.floor(diff / (1000*60*60*24)); const h = Math.floor((diff / (1000*60*60)) % 24);
    const m = Math.floor((diff / (1000*60)) % 60); const s = Math.floor((diff / 1000) % 60);
    document.getElementById('days').innerText = d.toString().padStart(2, '0');
    document.getElementById('hours').innerText = h.toString().padStart(2, '0');
    document.getElementById('mins').innerText = m.toString().padStart(2, '0');
    document.getElementById('secs').innerText = s.toString().padStart(2, '0');
  };
  setInterval(update, 1000); update();
}
initTimer();

// =========================================
// 6. FUNCIONES AUXILIARES (PESO MECANICO)
// =========================================
function getMechanicalWeight(number, targetPosition, historyData) {
    let count = 0;
    let totalDraws = 0;

    // Analizamos los ultimos 100 sorteos para capturar la tendencia actual de la maquina
    const recentData = historyData.slice(0, 100);

    recentData.forEach(row => {
        // Intentamos leer la posicion fisica (LOTO_pos1...pos6)
        // Si no existe la columna 'pos', usamos la 'n' (aunque 'n' suele estar ordenada,
        // si el CSV original tiene el orden de extraccion en 'n', funcionara igual).
        let valInPos = parseInt(row[`LOTO_pos${targetPosition}`]) || parseInt(row[`LOTO_n${targetPosition}`]);

        if (valInPos === number) {
            count++;
        }
        if (row.LOTO_n1) totalDraws++;
    });

    if (totalDraws === 0) return 1;

    let frequency = count / totalDraws;

    // Si el numero sale mas del 5% de las veces en esa posicion especifica, es un "favorito"
    if (frequency > 0.05) return 1.5;
    // Si nunca ha salido en esa posicion recientemente, penalizamos
    if (count === 0) return 0.5;

    return 1;
}

// =========================================
// 7. ANALISIS FORENSE
// =========================================
let forensicData = null;

// 1. Cargar el JSON silenciosamente al inicio
async function loadForensicBrain() {
    try {
        // Busca el archivo generado por el nuevo script Python
        const response = await fetch('data/loto_biometrics.json?nocache=' + new Date().getTime());

        if (!response.ok) throw new Error("Archivo de inteligencia no encontrado");

        forensicData = await response.json();

        // Actualizar fecha en el panel HTML
        const dateEl = document.getElementById('forensic-last-update');
        if (dateEl && forensicData.metadata) {
            dateEl.innerText = `Actualizado: ${forensicData.metadata.generated_at}`;
        }
        console.log("Cerebro Forense cargado correctamente.");

    } catch (e) {
        console.warn("No se pudo cargar loto_biometrics.json. Asegurate de correr analizador_forense.py");
        const output = document.getElementById('forensic-output');
        if(output) output.innerHTML = `<div style="color:var(--danger)">Falta el archivo 'loto_biometrics.json'.<br><small>Ejecuta el script Python analizador_forense.py primero.</small></div>`;
    }
}

// 2. Algoritmo de Seleccion Ponderada (Weighted Random)
// Elige un numero proporcional a su peso en esa posicion
function getWeightedNumber(weightsObj) {
    // weightsObj es { "1": 0.05, "2": 0.01 ... }
    const entries = Object.entries(weightsObj);
    let totalWeight = entries.reduce((acc, [num, w]) => acc + w, 0);
    let random = Math.random() * totalWeight;

    for (let [num, weight] of entries) {
        random -= weight;
        if (random <= 0) return parseInt(num);
    }
    // Fallback por si acaso
    return parseInt(entries[0][0]);
}

// 3. Funcion Principal de Generacion (Activada por los botones)
function generarPrediccionForense(gameMode) {
    const outputDiv = document.getElementById('forensic-output');

    if (!forensicData) {
        outputDiv.innerHTML = `<div style="color:orange; text-align:center;">Cargando inteligencia... intenta en 2 segundos.</div>`;
        loadForensicBrain(); // Reintento de carga
        return;
    }

    const game = forensicData.games[gameMode];
    if (!game) {
        outputDiv.innerHTML = `<div style="color:orange; text-align:center;">No hay datos forenses para <b>${gameMode}</b> en el archivo JSON.</div>`;
        return;
    }

    // Generar numeros basados en la posicion fisica
    let numbers = [];
    let detailsHTML = '<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap:10px; margin-top:15px;">';

    // Obtener las posiciones disponibles en este juego (generalmente 1 a 6)
    const availablePositions = Object.keys(game.positions).sort((a,b)=>a-b);

    for (let posKey of availablePositions) {
        let w = game.positions[posKey].weights;

        // Intentar sacar un numero
        let num = getWeightedNumber(w);
        let safety = 0;

        // Evitar duplicados en la misma jugada (re-roll si ya salio)
        while (numbers.includes(num) && safety < 50) {
            num = getWeightedNumber(w);
            safety++;
        }
        numbers.push(num);

        // Crear explicacion visual para "ADN de la Jugada"
        let chance = (w[num] * 100).toFixed(2);
        // Destacar si la probabilidad es alta (> 3.0% es alto para Loto)
        let isHot = chance > 3.0 ? 'color:var(--neon-cyan); font-weight:bold;' : 'color:var(--text-muted);';

        detailsHTML += `
            <div style="background:rgba(255,255,255,0.05); padding:8px; border-radius:4px; font-size:0.75rem; border:1px solid rgba(255,255,255,0.05);">
                <div style="color:var(--gold); font-size:0.65rem; text-transform:uppercase; letter-spacing:1px;">Posicion ${posKey}</div>
                <div style="font-size:1.3rem; font-weight:bold; color:white; margin:2px 0;">${num}</div>
                <div style="${isHot}">Peso: ${chance}%</div>
            </div>
        `;
    }

    // Ordenar numeros para la vista principal de bolas
    let sortedNumbers = [...numbers].sort((a,b) => a-b);

    // --- INTEGRACION CLAVE: ACTUALIZAR LA VARIABLE GLOBAL PARA GUARDADO ---
    currentGeneratedNumbers = sortedNumbers;

    // Renderizar todo el bloque
    outputDiv.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:10px; animation: fadeIn 0.5s ease;">
            <div style="text-align:center; color:var(--text-muted); font-size:0.8rem; margin-bottom:5px;">
                Sugerencia Forense para <span style="color:var(--neon-cyan); font-weight:bold;">${gameMode}</span>
            </div>

            <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-bottom:5px;">
                ${sortedNumbers.map(n =>
                    `<div style="width:50px; height:50px; border-radius:50%; background:var(--gold); color:black; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:1.4rem; box-shadow:0 0 15px rgba(255, 215, 0, 0.3);">
                        ${n}
                    </div>`
                ).join('')}
            </div>

            <div id="gen-actions-forensic" style="margin-top: 1rem; display: flex; justify-content: center; gap: 15px;">
                <button onclick="savePlay(true)" class="gen-btn" style="font-size:0.8rem; padding:0.8rem 1.5rem; background:#00ff41; color:black; border:none; box-shadow:0 0 15px rgba(0,255,65,0.3);">
                    <i data-lucide="ticket" style="width:16px; margin-right:5px;"></i> LA JUGUE!
                </button>
                <button onclick="savePlay(false)" class="gen-btn" style="font-size:0.8rem; padding:0.8rem 1.5rem; background:transparent; border:1px solid #a0aec0; color:#a0aec0; box-shadow:none;">
                    <i data-lucide="save" style="width:16px; margin-right:5px;"></i> Solo Guardar
                </button>
            </div>

            <div style="border-top:1px solid var(--border); padding-top:10px; margin-top:10px;">
                <div style="font-size:0.8rem; color:white; margin-bottom:5px; display:flex; align-items:center; gap:5px;">
                    <i data-lucide="microscope" width="14"></i> ADN DE LA JUGADA (Peso por Posicion Real)
                </div>
                ${detailsHTML}
            </div>
        </div>
    `;

    // Re-inicializar iconos dentro del nuevo HTML inyectado
    lucide.createIcons();
}

// Iniciar carga al abrir la pagina
window.addEventListener('DOMContentLoaded', loadForensicBrain);
