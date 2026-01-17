const CONFIG_JUEGOS = ["LOTO", "LOTO3", "LOTO4", "RACHA"];

async function loadPredictions() {
    try {
        const response = await fetch('dashboard_data.json');
        const rawData = await response.json();

        CONFIG_JUEGOS.forEach(j => { document.getElementById(`grid-${j}`).innerHTML = ''; });

        if (!rawData || rawData.length === 0) return;

        // Ordenar por sorteo y luego por confianza
        rawData.sort((a, b) => {
            if (b.sorteo_objetivo !== a.sorteo_objetivo) return b.sorteo_objetivo - a.sorteo_objetivo;
            return b.score_afinidad - a.score_afinidad;
        });

        CONFIG_JUEGOS.forEach(gameKey => {
            const container = document.getElementById(`grid-${gameKey}`);
            const filtered = rawData.filter(item => {
                if (!item.juego) return false;
                const juegoUpper = item.juego.toString().toUpperCase().trim();

                // Filtro exacto: LOTO no debe matchear LOTO3 o LOTO4
                if (gameKey === "LOTO") {
                    // Solo acepta "LOTO" exacto o variantes como "LOTO_HISTORIAL", pero NO "LOTO3" ni "LOTO4"
                    return juegoUpper === "LOTO" || (juegoUpper.startsWith("LOTO") && !juegoUpper.match(/^LOTO\d/));
                }
                // Para LOTO3, LOTO4, RACHA: match exacto o que empiece con el nombre
                return juegoUpper === gameKey || juegoUpper.startsWith(gameKey + "_");
            }).slice(0, 10);

            if (filtered.length > 0) {
                filtered.forEach(item => { renderCard(item, `grid-${gameKey}`); });
            } else {
                container.innerHTML = `<p class="empty-msg">No hay senales para ${gameKey}.</p>`;
            }
        });

    } catch (error) { console.error("Error:", error); }
}

// --- LOGICA DEL SEMAFORO ---
function getStatusInfo(score, isDisident) {
    if (isDisident) return { color: "#f43f5e", label: "DISIDENCIA" };
    if (score > 60) return { color: "#10b981", label: "ALTA" };
    if (score > 25) return { color: "#facc15", label: "MEDIA" };
    return { color: "#ef4444", label: "RUIDO" };
}

function renderCard(data, containerId) {
    // --- PARSEO INTELIGENTE DE NUMEROS ---
    let numerosArr;

    // Caso 1: Ya es un Array (Lista limpia de Python)
    if (Array.isArray(data.numeros)) {
        numerosArr = data.numeros;
    }
    // Caso 2: Es un String (Texto que parece lista)
    else if (typeof data.numeros === 'string') {
        try {
            // Limpiamos comillas simples de Python (') por dobles de JSON (")
            // y limpiamos espacios extra
            let cleanStr = data.numeros.replace(/'/g, '"').trim();

            // Si empieza con corchete, intentamos parseo JSON estandar
            if (cleanStr.startsWith('[')) {
                numerosArr = JSON.parse(cleanStr);
            } else {
                // Si no tiene corchetes (ej: "1, 2, 3"), separamos por comas
                numerosArr = cleanStr.split(',').map(n => parseInt(n.trim()));
            }
        } catch (e) {
            console.warn("Fallo parseo estricto, usando extraccion bruta para:", data.numeros);
            // ULTIMO RECURSO: Extraer solo los digitos con Regex (ignora cualquier basura)
            let matches = data.numeros.match(/\d+/g);
            numerosArr = matches ? matches.map(Number) : [0,0,0,0,0,0];
        }
    }
    // Caso 3: Es null, undefined u otra cosa
    else {
        numerosArr = [0, 0, 0, 0, 0, 0];
    }
    // ------------------------------------------

    const isDisident = data.nota_especial === 'ALERTA_DISIDENCIA';
    const status = getStatusInfo(data.score_afinidad, isDisident);

    let cardClass = "card";
    if (isDisident) cardClass += " disident-card";
    else if (data.score_afinidad > 60) cardClass += " high-conf";

    const fechaGen = data.fecha_generacion || "Desconocida";
    const fechaLanz = data.fecha_lanzamiento || "Pendiente";

    // Unir numeros con guion
    const numerosLegibles = Array.isArray(numerosArr) ? numerosArr.join(' - ') : "Error Formato";

    const html = `
        <div class="${cardClass}">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div>
                    <span class="tag" style="background:${status.color}">SORTEO #${data.sorteo_objetivo}</span>
                </div>
                <span style="font-weight:bold; font-size:0.75rem; color:${status.color}">
                    ${status.label}
                </span>
            </div>

            <div class="time-box">
                <div class="time-row">
                    <span class="time-label">Lanzamiento:</span>
                    <span class="time-value">${fechaLanz}</span>
                </div>
                <div class="generation-info">
                    <strong>Sonado el:</strong> ${fechaGen}
                </div>
            </div>

            <p class="numbers">${numerosLegibles}</p>

            <div class="confidence-bar" role="progressbar" aria-valuenow="${data.score_afinidad}" aria-valuemin="0" aria-valuemax="100" aria-label="Nivel de confianza: ${data.score_afinidad}%">
                <div class="confidence-fill"
                    style="width: ${Math.min(data.score_afinidad, 100)}%; background-color: ${status.color}">
                </div>
            </div>

            <div class="footer-info">
                <div>
                    <small style="color:#94a3b8; display:block; font-size:0.6rem;">CONFIANZA ML</small>
                    <span style="font-weight:bold; color:${status.color}">${data.score_afinidad}%</span>
                </div>
                <div style="text-align:right">
                    <small style="color:#64748b; font-size: 0.6rem;">ALGORITMO</small>
                    <small style="color:#94a3b8; display:block; font-size:0.7rem;">${data.algoritmo || 'General'}</small>
                </div>
            </div>
        </div>
    `;

    document.getElementById(containerId).insertAdjacentHTML('beforeend', html);
}

loadPredictions();
