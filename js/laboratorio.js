// =========================================================
// 1. CONFIGURACION DE FUENTES DE DATOS & REGLAS DE NEGOCIO
// =========================================================
const DATA_SOURCES = {
    'SIMS': 'data/LOTO_SIMULACIONES.csv',
    'JUGADAS': 'data/LOTO_JUGADAS.csv',
    'LOTO': 'data/LOTO_HISTORIAL_MAESTRO.csv',
    'LOTO3': 'data/LOTO3_MAESTRO.csv',
    'LOTO4': 'data/LOTO4_MAESTRO.csv',
    'RACHA': 'data/RACHA_MAESTRO.csv'
};

// CONFIGURACION DE ESTRATEGIA LOTO 3 (FLAT BETTING)
const ESTRATEGIA_LOTO3 = {
    exacta: 100,
    trio: 100,
    par: 100,
    terminacion: 100
};

// Funcion de Escalamiento (Ahora sera x1 porque la base es 100)
function calcularPremioEscalado(montoBaseCSV, apuestaUsuario) {
    if (!montoBaseCSV || montoBaseCSV === 0) return 0;
    // Si el CSV trae el premio para una apuesta de $100, esto devuelve el monto exacto.
    return montoBaseCSV * (apuestaUsuario / 100);
}

// --- ACTUALIZACION DE ALGORITMOS: AGREGADO ORACULO NEURAL ---
const UNIVERSE_CONFIG = {
    'LOTO': {
        algos: [
            {key: 'forense', label: 'Bio', color: '#58a6ff'},
            {key: 'gauss', label: 'Gauss', color: '#f1e05a'},
            {key: 'delta', label: 'Delta', color: '#20b2aa'},
            {key: 'markov', label: 'Markov', color: '#ff69b4'},
            {key: 'oraculo_neural_v3', label: 'Oraculo V3', color: '#8e44ad'},
            {key: 'oraculo_neural_v4', label: 'Oraculo V4', color: '#be58ff'},
            {key: 'consenso', label: 'Consenso', color: '#ffffff'}
        ],
        hits: [6, 5, 4, 3, 2, 1],
        cost: 1000
    },
    'LOTO3': {
        algos: [
            {key: 'forense', label: 'Bio', color: '#58a6ff'},
            {key: 'oraculo_neural_v3', label: 'Oraculo V3', color: '#8e44ad'},
            {key: 'oraculo_neural_v4', label: 'Oraculo V4', color: '#be58ff'},
            {key: 'consenso', label: 'Consenso', color: '#ffffff'}
        ],
        hits: [3, 2, 1],
        cost: 500
    },
    'LOTO4': {
        algos: [
            {key: 'forense', label: 'Bio', color: '#58a6ff'},
            {key: 'oraculo_neural_v3', label: 'Oraculo V3', color: '#8e44ad'},
            {key: 'oraculo_neural_v4', label: 'Oraculo V4', color: '#be58ff'},
            {key: 'consenso', label: 'Consenso', color: '#ffffff'}
        ],
        hits: [4, 3, 2, 1],
        cost: 500
    },
    'RACHA': {
        algos: [
            {key: 'forense', label: 'Bio', color: '#58a6ff'},
            {key: 'oraculo_neural_v3', label: 'Oraculo V3', color: '#8e44ad'},
            {key: 'oraculo_neural_v4', label: 'Oraculo V4', color: '#be58ff'},
            {key: 'consenso', label: 'Consenso', color: '#ffffff'}
        ],
        hits: [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        cost: 500
    }
};

// Estado Global de la Aplicacion
let RAW_SIMULATIONS = [];
let RAW_PLAYS = [];
let MASTERS = {};
let MASTERS_DATES = {};
let MASTERS_PRIZES = {};
let MASTERS_WINNERS = {};
let MASTERS_COMODIN = {};

let CURRENT_UNIVERSE = 'LOTO';
let CURRENT_CHART_MODE = 'hour';

let SORT_COL = 'target';
let SORT_DIR = 'desc';
let LOGS_SORT_COL = 'date';
let LOGS_SORT_DIR = 'desc';

// Inicializacion de Selectores
const hSel = document.getElementById('f-hora');
for(let i=0; i<24; i++) {
    let opt = document.createElement('option'); opt.value = i; opt.textContent = i.toString().padStart(2,'0')+":00"; hSel.appendChild(opt);
}

// Funcion auxiliar para colores transparentes en graficos
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// =========================================================
// 2. SISTEMA DE CARGA DE DATOS (DATA LOADER)
// =========================================================
async function loadAllData() {
    try {
        const promises = Object.entries(DATA_SOURCES).map(([key, url]) =>
            fetch(url + '?t=' + Date.now()).then(res => res.ok ? res.text() : null).then(text => ({key, text}))
        );

        const results = await Promise.all(promises);

        results.forEach(({key, text}) => {
            if (!text) return;
            if (key === 'SIMS') processSimulations(text);
            else if (key === 'JUGADAS') processPlays(text);
            else processMaster(key, text);
        });

        applyFilters();

    } catch (e) {
        console.error("Error critico cargando datos:", e);
        document.getElementById('last-update').textContent = "Error de Conexion";
        document.getElementById('last-update').style.background = "var(--danger)";
    }
}

// Procesador de Archivos Maestros (Historial + Premios + Ganadores)
function processMaster(gameKey, text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return;
    const headers = lines[0].split(',');

    // --- CONFIGURACION DE COLUMNAS DE NUMEROS ---
    let numCols = [];
    let comodinCol = -1;

    if (gameKey === 'LOTO') {
        numCols = ['LOTO_n1','LOTO_n2','LOTO_n3','LOTO_n4','LOTO_n5','LOTO_n6'];
        comodinCol = headers.indexOf('LOTO_comodin');
    }
    else if (gameKey === 'LOTO3') { numCols = ['n1','n2','n3']; }
    else if (gameKey === 'LOTO4') { numCols = ['n1','n2','n3','n4']; }
    else if (gameKey === 'RACHA') { numCols = ['n1','n2','n3','n4','n5','n6','n7','n8','n9','n10']; }

    const idxSorteo = headers.indexOf('sorteo');
    const idxFecha = headers.indexOf('fecha');
    const idxs = numCols.map(c => headers.indexOf(c));

    if (idxSorteo === -1) return;

    // --- MAPEOS PARA EXTRACCION ---
    const map = {};
    const dateMap = {};
    const prizeMap = {};
    const winnerMap = {};
    const comodinMap = {};

    // Mapeo Explicito de Columnas de Premios y Ganadores
    let colMap = {};
    let winnerColMap = {};

    if (gameKey === 'LOTO') {
        colMap = {
            'LOTO': headers.indexOf('LOTO_MONTO'),
            'SQUINA': headers.indexOf('SUPER_QUINA_5_ACIERTOS_COMODIN_MONTO'),
            'QUINA': headers.indexOf('QUINA_5_ACIERTOS_MONTO'),
            'SCUATERNA': headers.indexOf('SUPER_CUATERNA_4_ACIERTOS_COMODIN_MONTO'),
            'CUATERNA': headers.indexOf('CUATERNA_4_ACIERTOS_MONTO'),
            'STERNA': headers.indexOf('SUPER_TERNA_3_ACIERTOS_COMODIN_MONTO'),
            'TERNA': headers.indexOf('TERNA_3_ACIERTOS_MONTO'),
            'SDUPLA': headers.indexOf('SUPER_DUPLA_2_ACIERTOS_COMODIN_MONTO'),
            'POZO_REAL': headers.indexOf('LOTO_POZO_REAL')
        };
        winnerColMap = {
            'LOTO': headers.indexOf('LOTO_GANADORES'),
            'SQUINA': headers.indexOf('SUPER_QUINA_5_ACIERTOS_COMODIN_GANADORES'),
            'QUINA': headers.indexOf('QUINA_5_ACIERTOS_GANADORES'),
            'SCUATERNA': headers.indexOf('SUPER_CUATERNA_4_ACIERTOS_COMODIN_GANADORES'),
            'CUATERNA': headers.indexOf('CUATERNA_4_ACIERTOS_GANADORES'),
            'STERNA': headers.indexOf('SUPER_TERNA_3_ACIERTOS_COMODIN_GANADORES'),
            'TERNA': headers.indexOf('TERNA_3_ACIERTOS_GANADORES'),
            'SDUPLA': headers.indexOf('SUPER_DUPLA_2_ACIERTOS_COMODIN_GANADORES')
        };
    }
    else if (gameKey === 'LOTO4') {
        colMap = {
            '4P': headers.indexOf('4_PUNTOS_MONTO'),
            '3P': headers.indexOf('3_PUNTOS_MONTO'),
            '2P': headers.indexOf('2_PUNTOS_MONTO')
        };
        winnerColMap = {
            '4P': headers.indexOf('4_PUNTOS_GANADORES'),
            '3P': headers.indexOf('3_PUNTOS_GANADORES'),
            '2P': headers.indexOf('2_PUNTOS_GANADORES')
        };
    }
    // --- AQUI ESTABA EL FALTANTE: LOTO 3 ---
    else if (gameKey === 'LOTO3') {
        colMap = {
            'EXACTA_MONTO': headers.indexOf('EXACTA_MONTO'),
            'TRIO_PAR_MONTO': headers.indexOf('TRIO_PAR_MONTO'),
            'TRIO_AZAR_MONTO': headers.indexOf('TRIO_AZAR_MONTO'),
            'PAR_MONTO': headers.indexOf('PAR_MONTO'),
            'TERMINACION_MONTO': headers.indexOf('TERMINACION_MONTO')
        };
        winnerColMap = {
            'EXACTA': headers.indexOf('EXACTA_GANADORES'),
            'TRIO_PAR': headers.indexOf('TRIO_PAR_GANADORES'),
            'TRIO_AZAR': headers.indexOf('TRIO_AZAR_GANADORES'),
            'PAR': headers.indexOf('PAR_GANADORES'),
            'TERMINACION': headers.indexOf('TERMINACION_GANADORES')
        };
    }

    // --- ITERACION POR FILAS ---
    for (let i = 1; i < lines.length; i++) {
        const row = lines[i].split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);
        const sorteo = row[idxSorteo];
        if (!sorteo) continue;

        // 1. Numeros Ganadores
        const nums = idxs.map(idx => idx !== -1 ? parseInt(row[idx]) : null).filter(n => n !== null);
        map[sorteo] = nums;

        // 2. Fecha y Comodin
        if(idxFecha !== -1) dateMap[sorteo] = row[idxFecha].split(' ')[0];
        if(comodinCol !== -1) comodinMap[sorteo] = parseInt(row[comodinCol]);

        // 3. Extraccion Financiera (AHORA SI FUNCIONA PARA TODOS)
        prizeMap[sorteo] = {};
        winnerMap[sorteo] = {};

        // Extraer Montos ($)
        for (const [key, idx] of Object.entries(colMap)) {
            if (idx !== -1 && row[idx]) {
                let val = parseFloat(row[idx]);
                prizeMap[sorteo][key] = isNaN(val) ? 0 : val;
            } else {
                prizeMap[sorteo][key] = 0;
            }
        }
        // Extraer Ganadores (Personas)
        for (const [key, idx] of Object.entries(winnerColMap)) {
            if (idx !== -1 && row[idx]) {
                let val = parseInt(row[idx]);
                winnerMap[sorteo][key] = isNaN(val) ? 0 : val;
            } else {
                winnerMap[sorteo][key] = 0;
            }
        }
    }
    // Guardar en memoria global
    MASTERS[gameKey] = map;
    MASTERS_DATES[gameKey] = dateMap;
    MASTERS_PRIZES[gameKey] = prizeMap;
    MASTERS_WINNERS[gameKey] = winnerMap;
    MASTERS_COMODIN[gameKey] = comodinMap;
}

// Procesador de Simulaciones del Bot
function processSimulations(text) {
    const lines = text.trim().split('\n');
    const headers = lines[0].split(',');

    RAW_SIMULATIONS = lines.slice(1).map(line => {
        const parts = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);
        if (parts.length < 5) return null;

        let obj = {};
        try {
            obj.id = parts[0];
            obj.fechaStr = parts[1];
            let dtRaw = parts[1].replace(' ', 'T');
            obj.dateObj = new Date(dtRaw);
            if(isNaN(obj.dateObj)) obj.dateObj = new Date();

            if (headers.includes('juego')) {
                obj.juego = parts[2];
                obj.numeros = parts[3];
                obj.objetivo = parts[4];
                obj.estado = parts[5];
                obj.aciertos = parseInt(parts[6] || 0);
                obj.score = parseFloat(parts[7] || 0);
                obj.hora = parseInt(parts[8]);
                obj.algoritmo = parts[9] || 'unknown';
                obj.fechaLanzamiento = parts[11] ? parts[11].replace(/\r/g, '').trim() : '';
            } else {
                // Soporte Legacy
                obj.juego = 'LOTO';
                obj.numeros = parts[2];
                obj.objetivo = parts[3];
                obj.estado = parts[4];
                obj.aciertos = parseInt(parts[5] || 0);
                obj.score = parseFloat(parts[6] || 0);
                obj.hora = parseInt(parts[7]);
                obj.algoritmo = parts[8] || 'unknown';
                obj.fechaLanzamiento = '';
            }

            if(isNaN(obj.hora)) {
                obj.hora = obj.dateObj.getHours();
            }

            obj.numeros = obj.numeros.replace(/"/g, '');
            obj.algoritmo = obj.algoritmo.replace(/\r/g, '');

            return obj;
        } catch(e) { return null; }
    }).filter(x => x !== null).reverse();
}

// Procesador de Jugadas Reales (CSV Manual)
function processPlays(text) {
    const lines = text.trim().split('\n');
    RAW_PLAYS = lines.slice(1).map(line => {
        const p = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);
        if(p.length < 4) return null;

        // Solo nos interesan las que dicen "SI" en jugado
        if(p[3] !== 'SI') return null;

        return {
            numeros: p[2].replace(/"/g, ''),
            objetivo: p[5], // Sorteo objetivo
            juego: p[6] || 'LOTO' // Juego (Default Loto)
        };
    }).filter(x=>x);
}

// =========================================================
// 3. MOTOR FINANCIERO (THE MONEY ENGINE)
// =========================================================

// Funcion Nuclear: Calcula cuanto gano UNA sola jugada (VERSION BLINDADA)
function calculateWinningsDetailed(game, myNums, winNums, comodin, drawId) {
    if (!myNums || !winNums) return { amount: 0, category: '', formula: '' };

    // --- LOTO 3 ---
    if (game === 'LOTO3') {
        // Configuracion de Premios Fijos (Reglas Polla)
        const BASE_APUESTA = 100;
        const MULT_EXACTA = 400;
        const MULT_TRIO_PAR = 130;
        const MULT_TRIO_AZAR = 65;
        const MULT_PAR = 20;
        const MULT_TERM = 4;

        const p = myNums; // Prediccion [n1, n2, n3]
        const r = winNums; // Real [n1, n2, n3]

        // Analisis de Topologia (Que jugamos?)
        const uniqueMy = new Set(p).size;
        const juegaTrio = (uniqueMy === 2 || uniqueMy === 3); // Solo juega trio si hay 2 o 3 distintos

        let total = 0;
        let cats = [];
        let formulas = [];

        // A. EXACTA ($100 -> $40.000)
        // Coincidencia exacta en valor y posicion
        if (p[0] === r[0] && p[1] === r[1] && p[2] === r[2]) {
            total += BASE_APUESTA * MULT_EXACTA;
            cats.push("Exacta");
            formulas.push("$40.000");
        }

        // B. TRIO (Depende de Topologia)
        // Ordenamos para comparar conjuntos
        if (juegaTrio) {
            const pSort = [...p].sort((a,b)=>a-b).join(',');
            const rSort = [...r].sort((a,b)=>a-b).join(',');

            if (pSort === rSort) {
                if (uniqueMy === 2) {
                    // Trio Par (2 iguales, 1 distinto) -> $13.000
                    total += BASE_APUESTA * MULT_TRIO_PAR;
                    cats.push("Trio Par");
                    formulas.push("$13.000");
                } else if (uniqueMy === 3) {
                    // Trio Azar (3 distintos) -> $6.500
                    total += BASE_APUESTA * MULT_TRIO_AZAR;
                    cats.push("Trio Azar");
                    formulas.push("$6.500");
                }
            }
        }

        // C. PAR ($100 -> $2.000)
        // Se gana si aciertas Par Inicial O Par Final
        const parFront = (p[0] === r[0] && p[1] === r[1]);
        const parBack  = (p[1] === r[1] && p[2] === r[2]);

        if (parFront || parBack) {
            total += BASE_APUESTA * MULT_PAR;
            cats.push("Par");
            formulas.push("$2.000");
        }

        // D. TERMINACION ($100 -> $400)
        if (p[2] === r[2]) {
            total += BASE_APUESTA * MULT_TERM;
            cats.push("Terminacion");
            formulas.push("$400");
        }

        if (total > 0) return { amount: total, category: cats.join(" + "), formula: formulas.join(" + ") };
        return { amount: 0, category: "", formula: "" };
    }

    // --- LOTO CLASICO ---
    if (game === 'LOTO') {
        // BLINDAJE: Verificar que existan los datos maestros antes de leer
        const prizes = (MASTERS_PRIZES['LOTO'] && MASTERS_PRIZES['LOTO'][drawId]) ? MASTERS_PRIZES['LOTO'][drawId] : {};
        const winners = (MASTERS_WINNERS['LOTO'] && MASTERS_WINNERS['LOTO'][drawId]) ? MASTERS_WINNERS['LOTO'][drawId] : {};

        const hits = myNums.filter(n => winNums.includes(n)).length;
        const hasComodin = comodin && myNums.includes(comodin);

        const getPerPerson = (catKey, catName) => {
            const totalAmount = prizes[catKey] || 0;
            const count = winners[catKey] || 0;
            if (count > 0) {
                const individual = Math.floor(totalAmount / count);
                return { amount: individual, category: catName, formula: `$${totalAmount.toLocaleString()} / ${count}` };
            }
            return { amount: 0, category: "", formula: "" };
        };

        if (hits === 6) {
            let jackpot = prizes['LOTO'] || 0;
            let formula = "Pozo Repartido";
            if (jackpot === 0) {
                jackpot = prizes['POZO_REAL'] || 0;
                formula = "Pozo Acumulado (Simulacion)";
            }
            return { amount: jackpot, category: "LOTO 6 Aciertos", formula: formula };
        }
        if (hits === 5 && hasComodin) return getPerPerson('SQUINA', "Super Quina");
        if (hits === 5) return getPerPerson('QUINA', "Quina");
        if (hits === 4 && hasComodin) return getPerPerson('SCUATERNA', "Super Cuaterna");
        if (hits === 4) return getPerPerson('CUATERNA', "Cuaterna");
        if (hits === 3 && hasComodin) return getPerPerson('STERNA', "Super Terna");
        if (hits === 3) return getPerPerson('TERNA', "Terna");
        if (hits === 2 && hasComodin) return getPerPerson('SDUPLA', "Super Dupla");

        return { amount: 0, category: "", formula: "" };
    }

    // --- RACHA ---
    if (game === 'RACHA') {
        const winSet = new Set(winNums);
        const hits = myNums.filter(n => winSet.has(n)).length;
        if (hits === 10 || hits === 0) return { amount: 6000000, category: "Racha Max", formula: "Fijo" };
        if (hits === 9 || hits === 1) return { amount: 30000, category: "Racha Media", formula: "Fijo" };
        if (hits === 8 || hits === 2) return { amount: 1500, category: "Racha Baja", formula: "Fijo" };
        if (hits === 7 || hits === 3) return { amount: 500, category: "Racha Min", formula: "Fijo" };
        return { amount: 0, category: "", formula: "" };
    }

    // --- LOTO 4 ---
    if (game === 'LOTO4') {
        // BLINDAJE LOTO 4
        const prizes = (MASTERS_PRIZES['LOTO4'] && MASTERS_PRIZES['LOTO4'][drawId]) ? MASTERS_PRIZES['LOTO4'][drawId] : {};
        const winners = (MASTERS_WINNERS['LOTO4'] && MASTERS_WINNERS['LOTO4'][drawId]) ? MASTERS_WINNERS['LOTO4'][drawId] : {};

        const hits = myNums.filter(n => winNums.includes(n)).length;

        const getPerPerson = (catKey, catName) => {
            const totalAmount = prizes[catKey] || 0;
            const count = winners[catKey] || 0;
            if (count > 0) return { amount: Math.floor(totalAmount / count), category: catName, formula: `$${totalAmount.toLocaleString()} / ${count}` };
            return { amount: 0, category: "", formula: "" };
        };

        if (hits === 4) return getPerPerson('4P', "4 Puntos");
        if (hits === 3) return getPerPerson('3P', "3 Puntos");
        if (hits === 2) return getPerPerson('2P', "2 Puntos");
        return { amount: 0, category: "", formula: "" };
    }

    return { amount: 0, category: "", formula: "" };
}

// --- ORQUESTADOR FINANCIERO Y AUDITORIA ---
function calculateFinance(filteredSims, targetDraw) {
    const container = document.getElementById('financial-panel');
    const auditLog = document.getElementById('financial-audit-log');
    const auditBody = document.getElementById('audit-table-body');
    const config = UNIVERSE_CONFIG[CURRENT_UNIVERSE];

    // Limpieza inicial UI
    auditBody.innerHTML = '';

    // Si no hay sorteo seleccionado o configuracion, ocultar panel
    if (targetDraw === 'ALL' || !config) {
        container.style.display = 'none';
        auditLog.style.display = 'none';
        return;
    }
    container.style.display = 'grid'; // Mostrar KPIs
    auditLog.style.display = 'block'; // Mostrar Tabla Detalle

    // ---------------------------------------------------------
    // 1. FUNCION DE COSTO INTELIGENTE (Logica Aditiva)
    // ---------------------------------------------------------
    const getCost = (numsArr) => {
        // Para LOTO, RACHA, LOTO4 usamos el costo fijo global
        if (CURRENT_UNIVERSE !== 'LOTO3') {
            return config.cost;
        }

        // Para LOTO 3: Sumamos $100 por cada categoria activa
        const unique = new Set(numsArr).size;

        let costo = 0;
        costo += 100; // Exacta (Siempre va)
        costo += 100; // Par (Siempre va)
        costo += 100; // Terminacion (Siempre va)

        // Trio solo se cobra si la combinacion lo permite
        // (Si son 3 iguales como [0,0,0], NO se juega Trio)
        if (unique === 2 || unique === 3) {
            costo += 100;
        }

        return costo; // Retornara 400 (lo normal) o 300 (triple)
    };

    // ---------------------------------------------------------
    // 2. CALCULO HIPOTETICO (SIMULACIONES)
    // ---------------------------------------------------------
    let hypoInvest = 0;
    let hypoWin = 0;

    const winningNums = MASTERS[CURRENT_UNIVERSE][targetDraw];
    const comodin = MASTERS_COMODIN[CURRENT_UNIVERSE] ? MASTERS_COMODIN[CURRENT_UNIVERSE][targetDraw] : null;

    let winningRows = []; // Para guardar los ganadores y mostrarlos en tabla

    filteredSims.forEach(s => {
        let myNums = [];
        try { myNums = JSON.parse(s.numeros); } catch(e) { return; }

        // A. Sumar Costo Variable
        hypoInvest += getCost(myNums);

        // B. Calcular Ganancia (Solo si el sorteo ya ocurrio)
        if (winningNums) {
            const res = calculateWinningsDetailed(CURRENT_UNIVERSE, myNums, winningNums, comodin, targetDraw);
            if (res.amount > 0) {
                hypoWin += res.amount;
                // Guardamos para la tabla de detalle
                winningRows.push({ s, res, myNums });
            }
        }
    });

    // ---------------------------------------------------------
    // 3. RENDERIZADO DE TABLA DE DETALLE (GANADORES)
    // ---------------------------------------------------------
    // Ordenar: Primero Mayor Monto, luego Mas Reciente
    winningRows.sort((a, b) => {
        if (b.res.amount !== a.res.amount) return b.res.amount - a.res.amount;
        return b.s.dateObj - a.s.dateObj;
    });

    winningRows.forEach(row => {
        const s = row.s;
        const res = row.res;
        const myNums = row.myNums;

        // Formateo visual de numeros (Verdes si acertaron)
        const numsFormatted = myNums.map(n => {
            let style = "";
            if (winningNums.includes(n)) style = "color:var(--success); font-weight:bold;";
            if (n === comodin) style = "color:var(--gold); font-weight:bold; text-shadow:0 0 5px rgba(255,215,0,0.5);";
            return `<span style="${style}">${n}</span>`;
        }).join(", ");

        const tr = document.createElement('tr');
        tr.className = 'audit-row-win';
        tr.innerHTML = `
            <td>${s.fechaStr}</td>
            <td><span class="algo-badge" style="color:var(--text); border:1px solid var(--border);">${s.algoritmo.split('_')[0]}</span></td>
            <td style="font-family:monospace; font-size:0.9em;">[ ${numsFormatted} ]</td>
            <td style="text-align:center; font-weight:bold;">${s.aciertos}</td>
            <td>${res.category}</td>
            <td><small>${res.formula}</small></td>
            <td class="audit-money">$${res.amount.toLocaleString('es-CL')}</td>
        `;
        auditBody.appendChild(tr);
    });

    // ---------------------------------------------------------
    // 4. CALCULO REAL (LO QUE JUGASTE EN LOTO_JUGADAS.CSV)
    // ---------------------------------------------------------
    const realPlays = RAW_PLAYS.filter(p => p.juego === CURRENT_UNIVERSE && p.objetivo === targetDraw);
    let realInvest = 0;
    let realWin = 0;

    realPlays.forEach(play => {
        try {
            const myNums = JSON.parse(play.numeros);

            // A. Costo Real Variable
            realInvest += getCost(myNums);

            // B. Ganancia Real
            if (winningNums) {
                const res = calculateWinningsDetailed(CURRENT_UNIVERSE, myNums, winningNums, comodin, targetDraw);
                realWin += res.amount;
            }
        } catch(e) {}
    });

    // ---------------------------------------------------------
    // 5. ACTUALIZACION DE TARJETAS KPI (DASHBOARD)
    // ---------------------------------------------------------
    const fmt = (n) => "$" + n.toLocaleString('es-CL', {maximumFractionDigits: 0});

    document.getElementById('hypo-invest').textContent = fmt(hypoInvest);
    document.getElementById('hypo-win').textContent = fmt(hypoWin);
    document.getElementById('real-invest').textContent = fmt(realInvest);
    document.getElementById('real-win').textContent = fmt(realWin);

    // Colores Dinamicos (Verde si ganancia >= inversion, Rojo si perdida)
    document.getElementById('hypo-win').style.color = hypoWin >= hypoInvest ? 'var(--money)' : 'var(--loss)';
    document.getElementById('real-win').style.color = realWin >= realInvest ? 'var(--warning)' : 'var(--loss)';

    // Mensaje si no hubo ganadores simulados
    if (hypoWin === 0) {
        auditBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">Ninguna simulacion obtuvo premio monetario en este sorteo.</td></tr>';
    }
}

// =========================================================
// 4. FUNCIONES DE UI Y NAVEGACION
// =========================================================
function switchUniverse(gameId) {
    CURRENT_UNIVERSE = gameId;
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if(btn.getAttribute('data-game') === gameId) {
            btn.classList.add('active');
        }
    });
    resetFilters();
    // NUEVO: Renderizar plan seguro si corresponde
    setTimeout(() => renderSafePlanLoto3(), 50);
}

function applyFilters() {
    const data = getFilteredData();
    updateKPIs(data);
    updateSorteoSelector(data);
    renderTable(data);
    calculateAndRenderAggregate(data);
    updateDashboardCharts(data);
    renderFinancialTable(data);

    const selectedDraw = document.getElementById('f-sorteo').value;
    calculateFinance(data, selectedDraw);

    renderSafePlanLoto3();
    updateEvolutionChart();
}

function getFilteredData() {
    let data = RAW_SIMULATIONS.filter(d => d.juego === CURRENT_UNIVERSE);
    const fSorteo = document.getElementById('f-sorteo').value;
    const fAlgo = document.getElementById('f-algo').value;
    const fDia = document.getElementById('f-dia').value;
    const fHora = document.getElementById('f-hora').value;
    return data.filter(d => {
        if (fSorteo !== 'ALL' && d.objetivo !== fSorteo) return false;
        // --- FILTRO DE ALGORITMO ACTUALIZADO PARA ORACULO ---
        if (fAlgo !== 'ALL') {
            if (d.algoritmo === fAlgo) return true;
            if (!d.algoritmo.includes(fAlgo)) return false;
        }
        if (fDia !== 'ALL' && d.dateObj.getDay().toString() !== fDia) return false;
        if (fHora !== 'ALL' && d.hora.toString() !== fHora) return false;
        return true;
    });
}
function updateSorteoSelector(data) {
    const currentVal = document.getElementById('f-sorteo').value;
    const unique = [...new Set(data.map(d => d.objetivo))];
    const sel = document.getElementById('f-sorteo');
    sel.innerHTML = '<option value="ALL">Todos los Sorteos</option>';
    unique.forEach(u => {
        let opt = document.createElement('option'); opt.value = u; opt.textContent = "#" + u;
        sel.appendChild(opt);
    });
    if (unique.includes(currentVal)) sel.value = currentVal;
}
function formatFechaLanzamiento(fechaStr) {
    // Convierte "18/01/2026 21:00" a "sab 18, a las 21:00"
    if (!fechaStr) return '';
    try {
        const diasSemana = ['dom', 'lun', 'mar', 'mie', 'jue', 'vie', 'sab'];
        const [fechaPart, horaPart] = fechaStr.split(' ');
        const [dia, mes, anio] = fechaPart.split('/').map(Number);
        const fecha = new Date(anio, mes - 1, dia);
        const diaSemana = diasSemana[fecha.getDay()];
        return `(${diaSemana} ${dia}, a las ${horaPart})`;
    } catch(e) {
        return '';
    }
}
function parseTargetDate(str) {
    if (!str) return null;
    try {
        const [dPart, tPart] = str.split(' ');
        const [d, m, y] = dPart.split('/').map(Number);
        const [h, min] = tPart.split(':').map(Number);
        return new Date(y, m - 1, d, h, min);
    } catch(e) { return null; }
}

function updateKPIs(data) {
    document.getElementById('total-sims').textContent = data.length;
    if (data.length) {
        const item = data[0];
        const sorteoInfo = "#" + item.objetivo;
        const fechaInfo = formatFechaLanzamiento(item.fechaLanzamiento);
        
        const targetDate = parseTargetDate(item.fechaLanzamiento);
        const now = new Date();
        // Si ya pasaron 10 minutos del sorteo, lo marcamos como finalizado
        const isPast = targetDate && (now > new Date(targetDate.getTime() + 10*60*1000));
        
        const targetEl = document.getElementById('target-draw');
        targetEl.innerHTML = sorteoInfo + " " + fechaInfo;
        
        if (isPast) {
            targetEl.innerHTML += ` <span style="font-size:0.5em; background:var(--danger); color:white; padding:2px 5px; border-radius:4px; vertical-align:middle; margin-left:5px;">CERRADO</span>`;
            targetEl.style.opacity = "0.7";
        } else {
            targetEl.style.opacity = "1";
        }
    } else {
        document.getElementById('target-draw').textContent = "--";
    }

    document.getElementById('last-update').textContent = data.length ? data[0].fechaStr.split(' ')[1] : "--";
    const auditados = data.filter(d => d.estado === 'AUDITADO');
    const avg = auditados.length ? (auditados.reduce((a,b)=>a+b.score,0)/auditados.length).toFixed(1) : 0;
    document.getElementById('avg-score').textContent = avg + "%";
}
function renderTable(data) {
    data.sort((a,b) => {
        let valA = a[LOGS_SORT_COL], valB = b[LOGS_SORT_COL];
        if (LOGS_SORT_COL === 'date') { valA = a.id; valB = b.id; }
        if (LOGS_SORT_COL === 'target') { valA = parseInt(a.objetivo); valB = parseInt(b.objetivo); }
        return LOGS_SORT_DIR === 'asc' ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
    });
    const tbody = document.querySelector('#logs-table tbody');
    tbody.innerHTML = '';
    document.getElementById('filtered-count').textContent = `Mostrando ${Math.min(data.length, 50)} de ${data.length}`;
    data.slice(0, 50).forEach(row => {
        const tr = document.createElement('tr');
        let algoClass = 'algo-badge';
        // --- DETECCION DE CLASE CSS PARA ORACULO ---
        if(row.algoritmo.includes('forense')) algoClass += ' algo-bio';
        else if(row.algoritmo.includes('gauss')) algoClass += ' algo-gauss';
        else if(row.algoritmo.includes('delta')) algoClass += ' algo-delta';
        else if(row.algoritmo.includes('markov')) algoClass += ' algo-markov';
        else if(row.algoritmo.includes('oraculo_neural_v3')) algoClass += ' algo-v3';
        else if(row.algoritmo.includes('oraculo_neural_v4')) algoClass += ' algo-v4';
        else if(row.algoritmo.includes('consenso')) algoClass += ' algo-consenso';

        const realNums = MASTERS[CURRENT_UNIVERSE] ? MASTERS[CURRENT_UNIVERSE][row.objetivo] : [];
        const myNums = row.numeros.replace('[','').replace(']','').split(',').map(n=>parseInt(n.trim()));
        let numsHtml = myNums.map(n => {
            if (realNums && realNums.includes(n)) return `<span class="num-badge match-exact">${n}</span>`;
            return `<span class="num-badge match-far">${n}</span>`;
        }).join('');
        const playedKey = `played_${row.id}`;
        const isPlayed = localStorage.getItem(playedKey);
        const btnHtml = isPlayed
            ? `<button class="btn-action btn-disabled"><i data-lucide="check" width="12"></i> Jugado</button>`
            : `<button class="btn-action" onclick="savePlay(this, '${row.numeros}', '${row.id}')"><i data-lucide="ticket" width="12"></i> Jugar</button>`;
        tr.innerHTML = `
            <td>${row.fechaStr.slice(5, 16)}</td>
            <td><span class="${algoClass}">${row.algoritmo.split('_')[0]}</span></td>
            <td>#${row.objetivo}</td>
            <td>${numsHtml}</td>
            <td class="${row.estado==='AUDITADO'?'audited':'pending'}">${row.estado}</td>
            <td><b>${row.estado==='AUDITADO'?row.score+'%':'-'}</b></td>
            <td>${btnHtml}</td>
        `;
        tbody.appendChild(tr);
    });
    lucide.createIcons();
}
function calculateAndRenderAggregate(data) {
    try {
        const gameConfig = UNIVERSE_CONFIG[CURRENT_UNIVERSE] || UNIVERSE_CONFIG['LOTO'];
        const thead = document.getElementById('agg-head');

        let headerHTML = `
            <tr>
                <th class="sortable-header" onclick="sortAggregate('target')">Sorteo</th>
                <th class="sortable-header" onclick="sortAggregate('count')" style="text-align:center;">Cant.</th>
                <th style="min-width:200px;">Sorteo Real (Aciertos Globales)</th>
                <th>Mejor Prediccion</th>
                <th class="sortable-header" onclick="sortAggregate('avgTotal')" style="text-align:center;">Global</th>`;

        gameConfig.algos.forEach(algo => { headerHTML += `<th style="text-align:center; color:${algo.color};">${algo.label}</th>`; });
        gameConfig.hits.forEach(hits => {
            let color = '#8b949e';
            if(hits >= 6) color = '#ff00ff'; else if(hits >= 4) color = '#00f2ff'; else if(hits === 3 && CURRENT_UNIVERSE === 'LOTO3') color = '#ff00ff';
            headerHTML += `<th style="text-align:center; color:${color};">${hits}A</th>`;
        });
        headerHTML += `</tr>`;
        thead.innerHTML = headerHTML;

        const groups = {};
        data.forEach(d => {
            if (!groups[d.objetivo]) {
                groups[d.objetivo] = { target: parseInt(d.objetivo), count: 0, scores: [], algoScores: {}, bestRow: null, maxScore: -1, all_numbers: [], hitsCount: {} };
                gameConfig.algos.forEach(a => groups[d.objetivo].algoScores[a.key] = []);
                gameConfig.hits.forEach(h => groups[d.objetivo].hitsCount[h] = 0);
            }
            const g = groups[d.objetivo];
            g.count++;
            const nums = d.numeros.replace('[', '').replace(']', '').split(',').map(n=>parseInt(n.trim()));
            g.all_numbers.push(...nums);

            if (d.estado === 'AUDITADO') {
                g.scores.push(d.score);

                gameConfig.algos.forEach(a => {
                    if(d.algoritmo.includes(a.key)) {
                        g.algoScores[a.key].push(d.score);
                    }
                });
                if (d.score > g.maxScore) { g.maxScore = d.score; g.bestRow = d; }
                if (d.aciertos !== undefined && g.hitsCount[d.aciertos] !== undefined) { g.hitsCount[d.aciertos]++; }
            }
        });

        const rows = Object.values(groups).sort((a, b) => b.target - a.target);
        const tbody = document.getElementById('aggregate-body');
        tbody.innerHTML = '';

        rows.forEach(g => {
            const tr = document.createElement('tr');
            const dateStr = (MASTERS_DATES[CURRENT_UNIVERSE] && MASTERS_DATES[CURRENT_UNIVERSE][g.target]) ? MASTERS_DATES[CURRENT_UNIVERSE][g.target] : 'N/A';
            const realNums = (MASTERS[CURRENT_UNIVERSE] && MASTERS[CURRENT_UNIVERSE][g.target]) ? MASTERS[CURRENT_UNIVERSE][g.target] : [];

            const counts = {};
            g.all_numbers.forEach(n => { counts[n] = (counts[n] || 0) + 1; });

            let realHtml = '-';
            if (realNums && realNums.length > 0) {
                realHtml = realNums.map(n => {
                    const count = counts[n] || 0;
                    return `<div style="display:inline-block; margin:1px; padding:2px 4px; background:rgba(46,160,67,0.15); border:1px solid #2ea043; border-radius:4px; font-size:0.8em;"><b>${n}</b> <span style="color:#aaa; font-size:0.8em;">(${count})</span></div>`;
                }).join(' ');
            }

            let bestHtml = '-';
            if (g.bestRow) {
                const bNums = g.bestRow.numeros.replace('[','').replace(']','').split(',').map(n=>parseInt(n.trim()));
                const bHtml = bNums.map(n => {
                    if(realNums.includes(n)) return `<span class="num-badge match-exact">${n}</span>`;
                    return `<span class="num-badge match-far">${n}</span>`;
                }).join('');
                let badge = '';
                if(g.bestRow.algoritmo.includes('gauss')) badge = 'Gauss';
                else if(g.bestRow.algoritmo.includes('delta')) badge = 'Delta';
                else if(g.bestRow.algoritmo.includes('markov')) badge = 'Markov';
                else if(g.bestRow.algoritmo.includes('oraculo')) badge = 'Oraculo';
                else if(g.bestRow.algoritmo.includes('consenso')) badge = 'Consenso';
                else badge = 'Bio';
                bestHtml = `<div><span style="margin-right:5px;">${badge}</span>${bHtml} <small>(${g.maxScore}%)</small></div>`;
            }

            const avg = arr => arr.length ? (arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(0)+'%' : '-';

            let rowHTML = `
                <td><span class="draw-badge" title="Fecha: ${dateStr}">#${g.target}</span></td>
                <td style="text-align:center;">${g.count}</td>
                <td>${realHtml}</td>
                <td>${bestHtml}</td>
                <td style="text-align:center;"><b>${avg(g.scores)}</b></td>`;

            gameConfig.algos.forEach(a => {
                rowHTML += `<td style="text-align:center; color:${a.color};">${avg(g.algoScores[a.key])}</td>`;
            });

            gameConfig.hits.forEach(h => {
                let styleClass = 'hit-col-low'; if(h >= 6) styleClass = 'hit-col-high'; else if(h >= 4) styleClass = 'hit-col-mid';
                let val = g.hitsCount[h]; let valDisplay = val > 0 ? `<span class="${styleClass}">${val}</span>` : `<span class="hit-col-dim">-</span>`;
                rowHTML += `<td style="text-align:center;">${valDisplay}</td>`;
            });

            tr.innerHTML = rowHTML;
            tbody.appendChild(tr);
        });
    } catch(e) { console.error("Error Tabla Resumen:", e); }
}

function renderFinancialTable(data) {
    try {
        const gameConfig = UNIVERSE_CONFIG[CURRENT_UNIVERSE] || UNIVERSE_CONFIG['LOTO'];
        const thead = document.getElementById('fin-head');
        const tbody = document.getElementById('fin-body');

        // 1. ENCABEZADOS
        let headerHTML = `
            <tr>
                <th style="background:#1a1a1a;">Sorteo</th>
                <th style="text-align:center; background:#1a1a1a;">Total Sims</th>
                <th style="text-align:center; background:#1a1a1a; color:var(--success);">Ganadoras</th>
                <th style="text-align:center; background:#1a1a1a; color:var(--loss);">No Ganadoras</th>
                <th style="text-align:right; background:#222; border-left:2px solid var(--border); color:var(--gold);">POZO HIPOTETICO</th>
        `;

        gameConfig.algos.forEach(algo => {
            headerHTML += `
                <th style="text-align:center; border-left:1px solid var(--border); font-size:0.8em; color:${algo.color};" colspan="2">
                    ${algo.label}<br>
                    <span style="color:var(--text-muted); font-size:0.9em;">(Inv | Gan)</span>
                </th>`;
        });
        headerHTML += `</tr>`;
        thead.innerHTML = headerHTML;

        // 2. AGRUPAR
        const groups = {};
        data.forEach(d => {
            const t = parseInt(d.objetivo);
            if (isNaN(t)) return; // Proteccion contra basura
            if (!groups[t]) {
                groups[t] = { target: t, sims: [], count: 0, winners: 0, losers: 0 };
            }
            groups[t].sims.push(d);
            groups[t].count++;
        });

        // 3. CALCULAR
        const sortedTargets = Object.keys(groups).map(k => parseInt(k)).sort((a,b) => a - b);
        let cumulativeBalance = 0;

        const processedRows = sortedTargets.map(target => {
            const g = groups[target];
            const realNums = MASTERS[CURRENT_UNIVERSE] ? MASTERS[CURRENT_UNIVERSE][target] : [];
            const comodin = (MASTERS_COMODIN[CURRENT_UNIVERSE] && MASTERS_COMODIN[CURRENT_UNIVERSE][target]) ? MASTERS_COMODIN[CURRENT_UNIVERSE][target] : null;
            const costPerSim = gameConfig.cost;

            let drawInvest = 0;
            let drawWin = 0;
            let algoStats = {};
            gameConfig.algos.forEach(a => algoStats[a.key] = {inv: 0, win: 0});

            g.sims.forEach(s => {
                let algoKey = null;
                gameConfig.algos.forEach(a => {
                    if(s.algoritmo.includes(a.key)) algoKey = a.key;
                });

                drawInvest += costPerSim;
                if(algoKey && algoStats[algoKey]) algoStats[algoKey].inv += costPerSim;

                let winAmount = 0;
                if (realNums && realNums.length > 0) {
                    try {
                        const myNums = JSON.parse(s.numeros);
                        const res = calculateWinningsDetailed(CURRENT_UNIVERSE, myNums, realNums, comodin, target);
                        winAmount = res.amount;
                    } catch(e) {}
                }

                drawWin += winAmount;
                if(algoKey && algoStats[algoKey]) algoStats[algoKey].win += winAmount;

                if (winAmount > 0) g.winners++; else g.losers++;
            });

            const netResult = drawWin - drawInvest;
            cumulativeBalance += netResult;

            return {
                target: target,
                count: g.count,
                winners: g.winners,
                losers: g.losers,
                pozo: cumulativeBalance,
                algoStats: algoStats
            };
        });

        // 4. RENDERIZAR
        tbody.innerHTML = '';
        processedRows.reverse().forEach(row => {
            const tr = document.createElement('tr');
            const fmt = (n) => "$" + n.toLocaleString('es-CL');
            const fmtCompact = (n) => n >= 1000000 ? (n/1000000).toFixed(1)+"M" : (n >= 1000 ? (n/1000).toFixed(0)+"k" : n);

            const colorPozo = row.pozo >= 0 ? 'var(--money)' : 'var(--loss)';
            const signPozo = row.pozo > 0 ? '+' : '';

            let html = `
                <td style="font-weight:bold;">#${row.target}</td>
                <td style="text-align:center;">${row.count}</td>
                <td style="text-align:center; color:var(--success); font-weight:bold;">${row.winners}</td>
                <td style="text-align:center; color:var(--text-muted);">${row.losers}</td>
                <td style="text-align:right; font-family:monospace; font-size:1.1em; color:${colorPozo}; border-left:2px solid var(--border); background:rgba(0,0,0,0.2);">
                    ${signPozo}${fmt(row.pozo)}
                </td>
            `;

            gameConfig.algos.forEach(a => {
                const st = row.algoStats[a.key];
                if (!st) { html += `<td colspan="2"></td>`; return; }
                const profit = st.win - st.inv;
                const colorProfit = profit >= 0 ? 'var(--money)' : '#ff3b5c';
                const bg = profit > 0 ? 'rgba(0,255,65,0.05)' : 'transparent';

                html += `
                    <td style="text-align:right; border-left:1px solid var(--border); font-size:0.85em; color:var(--text-muted); background:${bg};" title="Inversion: ${fmt(st.inv)}">-${fmtCompact(st.inv)}</td>
                    <td style="text-align:right; font-size:0.85em; color:${colorProfit}; font-weight:bold; background:${bg};" title="Ganancia: ${fmt(st.win)}">${st.win > 0 ? '+' : ''}${fmtCompact(st.win)}</td>
                `;
            });

            tr.innerHTML = html;
            tbody.appendChild(tr);
        });

    } catch(e) {
        console.error("Error en Tabla Financiera:", e);
    }
}

function updateDashboardCharts(data) {
    const ctx = document.getElementById('mainChart').getContext('2d');

    // Destruir grafico previo si existe para evitar superposiciones
    if(window.myChart) window.myChart.destroy();

    // Filtrar solo los datos que ya tienen veredicto del Juez
    const auditados = data.filter(d => d.estado === 'AUDITADO');
    const gameConfig = UNIVERSE_CONFIG[CURRENT_UNIVERSE] || UNIVERSE_CONFIG['LOTO'];

    let labels = [];
    let buckets = {};

    // 1. CONFIGURAR ETIQUETAS Y CUBETAS SEGUN EL MODO (HORA/DIA/MES)
    if (CURRENT_CHART_MODE === 'hour') {
        labels = Array.from({length: 24}, (_, i) => `${i}:00`);
        labels.forEach((_, i) => buckets[i] = {});

        auditados.forEach(d => {
            let h = d.hora;
            if (isNaN(h)) h = d.dateObj.getHours();
            if (buckets[h]) {
                gameConfig.algos.forEach(a => {
                    if(d.algoritmo.includes(a.key)) {
                        if(!buckets[h][a.key]) buckets[h][a.key] = [];
                        buckets[h][a.key].push(d.score);
                    }
                });
            }
        });
    } else if (CURRENT_CHART_MODE === 'day') {
        labels = ['Dom','Lun','Mar','Mie','Jue','Vie','Sab'];
        labels.forEach((_, i) => buckets[i] = {});

        auditados.forEach(d => {
            let day = d.dateObj.getDay();
            if (buckets[day]) {
                gameConfig.algos.forEach(a => {
                    if(d.algoritmo.includes(a.key)) {
                        if(!buckets[day][a.key]) buckets[day][a.key] = [];
                        buckets[day][a.key].push(d.score);
                    }
                });
            }
        });
    } else if (CURRENT_CHART_MODE === 'month') {
        labels = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        labels.forEach((_, i) => buckets[i] = {});

        auditados.forEach(d => {
            let m = d.dateObj.getMonth();
            if (buckets[m]) {
                gameConfig.algos.forEach(a => {
                    if(d.algoritmo.includes(a.key)) {
                        if(!buckets[m][a.key]) buckets[m][a.key] = [];
                        buckets[m][a.key].push(d.score);
                    }
                });
            }
        });
    }

    // 2. TRANSFORMAR DATOS DE CUBETAS A DATASETS DE CHART.JS
    let datasets = gameConfig.algos.map(a => {
        let dataPoints = labels.map((_, i) => {
            let scores = buckets[i] ? buckets[i][a.key] : [];
            // Calculamos el promedio de afinidad por cada punto
            return scores && scores.length ? (scores.reduce((sum, val) => sum + val, 0) / scores.length).toFixed(1) : 0;
        });

        return {
            label: a.label,
            data: dataPoints,
            borderColor: a.color,
            backgroundColor: hexToRgba(a.color, 0.2),
            borderWidth: a.key.includes('consenso') ? 3 : 2,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 6,
            // Telemetria extra: guardamos cuantas simulaciones hay por punto para el tooltip
            counts: labels.map((_, i) => buckets[i] && buckets[i][a.key] ? buckets[i][a.key].length : 0)
        };
    });

    // 3. ACTUALIZAR KPI DE "MEJOR MOMENTO" (Usando el Consenso como referencia)
    let maxVal = 0, bestLbl = '--';
    const referenceDS = datasets.find(d => d.label.includes('Consenso')) || datasets[0];
    if(referenceDS) {
        referenceDS.data.forEach((v, i) => {
            if(parseFloat(v) > maxVal) {
                maxVal = parseFloat(v);
                bestLbl = labels[i];
            }
        });
    }
    document.getElementById('best-moment').textContent = bestLbl;

    // 4. INSTANCIAR EL GRAFICO FINAL
    window.myChart = new Chart(ctx, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#30363d' },
                    ticks: { color: '#8b949e', callback: value => value + '%' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#8b949e' }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#c9d1d9',
                        font: { family: "'JetBrains Mono', monospace", size: 11 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(22, 27, 34, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#c9d1d9',
                    borderColor: '#30363d',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) label += context.parsed.y + '%';
                            const count = context.dataset.counts[context.dataIndex];
                            if (count > 0) label += ` (${count} sims)`;
                            return label;
                        }
                    }
                }
            }
        }
    });
}

function resetFilters() { document.getElementById('f-sorteo').value = 'ALL'; document.getElementById('f-algo').value = 'ALL'; applyFilters(); }
function sortLogs(col) { LOGS_SORT_COL = col; LOGS_SORT_DIR = LOGS_SORT_DIR === 'asc' ? 'desc' : 'asc'; applyFilters(); }
function sortAggregate(col) { SORT_COL = col; SORT_DIR = SORT_DIR === 'asc' ? 'desc' : 'asc'; applyFilters(); }
function switchChartView(mode) { CURRENT_CHART_MODE = mode; applyFilters(); }
async function savePlay(btn, numsStr, id) { const originalContent = btn.innerHTML; btn.innerHTML = '...'; btn.disabled = true; const GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwBZd2vTrvxVdTjJnLoK2vMCR90qJqyH3ZfSDkNK4_n0aFYe3jCoeIZ3R58XNQBM1xQ3A/exec"; try { let numbers = JSON.parse(numsStr); await fetch(GOOGLE_SCRIPT_URL, { method: 'POST', mode: 'no-cors', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ numeros: numbers, jugado: "SI" }) }); localStorage.setItem(`played_${id}`, 'true'); btn.innerHTML = '<i data-lucide="check" width="12"></i> Listo'; btn.classList.add('btn-disabled'); lucide.createIcons(); } catch (error) { console.error("Error guardando jugada:", error); btn.innerHTML = '<i data-lucide="x" width="12"></i> Error'; btn.disabled = false; setTimeout(() => { btn.innerHTML = originalContent; lucide.createIcons(); }, 3000); } }

// =========================================================
// 5. MOTOR DE PLAN SEGURO (LOTO 3) - NUEVO MODULO
// =========================================================
function renderSafePlanLoto3() {
    const container = document.getElementById('loto3-safe-plan');

    // 1. Solo activar si estamos en LOTO 3
    if (CURRENT_UNIVERSE !== 'LOTO3') {
        container.style.display = 'none';
        return;
    }

    // 2. Obtener datos basicos
    // Analizamos todo el historial auditado
    const allLoto3 = RAW_SIMULATIONS.filter(d => d.juego === 'LOTO3');
    const audited = allLoto3.filter(d => d.estado === 'AUDITADO').sort((a,b) => a.id - b.id);

    // Ventana de analisis: Ultimos 60 juegos auditados
    const recentHistory = audited.slice(-60);

    if (recentHistory.length < 10) {
        container.style.display = 'none';
        return;
    }

    // 3. Calcular Metricas por Algoritmo
    const stats = {};
    recentHistory.forEach(row => {
        const algo = row.algoritmo;
        if (!stats[algo]) stats[algo] = { count: 0, hits1: 0, hits2: 0 };

        stats[algo].count++;
        if (row.aciertos >= 1) stats[algo].hits1++;
        if (row.aciertos >= 2) stats[algo].hits2++;
    });

    // 4. Seleccionar el Campeon
    let bestAlgo = null;
    let maxPower = -1;

    Object.keys(stats).forEach(algo => {
        const s = stats[algo];
        const powerRate = (s.hits2 / s.count) * 100;
        const safetyRate = (s.hits1 / s.count) * 100;

        // Criterio: Priorizar Poder, pero requerir minima data (5 juegos)
        if (s.count >= 5) {
            if (powerRate > maxPower) {
                maxPower = powerRate;
                bestAlgo = algo;
            } else if (powerRate === maxPower) {
                if (bestAlgo && safetyRate > (stats[bestAlgo].hits1 / stats[bestAlgo].count * 100)) {
                    bestAlgo = algo;
                }
            }
        }
    });

    if (!bestAlgo) {
        container.style.display = 'none';
        return;
    }

    // 5. Buscar prediccion PENDIENTE para el ganador
    let targetDraw = document.getElementById('f-sorteo').value;

    if (targetDraw === 'ALL') {
        const pending = allLoto3.filter(d => d.estado === 'PENDIENTE');
        if (pending.length > 0) {
            targetDraw = pending[0].objetivo;
        } else {
            container.style.display = 'none';
            return;
        }
    }

    const candidates = allLoto3.filter(d =>
        d.estado === 'PENDIENTE' &&
        d.objetivo == targetDraw &&
        d.algoritmo === bestAlgo
    );

    if (candidates.length === 0) {
        container.style.display = 'none';
        return;
    }

    // Tomamos la mas reciente
    const winnerRow = candidates.sort((a,b) => b.id - a.id)[0];
    const nums = JSON.parse(winnerRow.numeros);

    // 6. RENDERIZAR
    container.style.display = 'block';

    document.getElementById('plan-algo-name').textContent = bestAlgo.toUpperCase().replace('_', ' ');
    document.getElementById('plan-target').textContent = targetDraw;

    document.getElementById('plan-n1').textContent = nums[0];
    document.getElementById('plan-n2').textContent = nums[1];
    document.getElementById('plan-n3').textContent = nums[2];
}

// Iniciar
loadAllData();

// --- VARIABLES GLOBALES PARA EL GRAFICO ---
let rawSimulationData = [];
let evolutionChartInstance = null;

// 1. INICIADOR DEL TRANSPLANTE
// Agrega esta llamada al inicio, cuando cargues la pagina
function initLaboratorio() {
    console.log("Iniciando protocolos del Laboratorio...");
    loadSimulations();
    lucide.createIcons();
}

// 2. CARGA DE DATOS (CSV DE SIMULACIONES)
function loadSimulations() {
    Papa.parse('data/LOTO_SIMULACIONES.csv', {
        download: true,
        header: true,
        skipEmptyLines: true,
        complete: function(results) {
            rawSimulationData = results.data;
            console.log(`Datos historicos cargados: ${rawSimulationData.length} registros.`);
            updateEvolutionChart(); // Render inicial
        },
        error: function(err) {
            console.error("Error cargando simulaciones:", err);
        }
    });
}

// 3. LOGICA DE PROCESAMIENTO Y RENDERIZADO
// =========================================================
// NUEVA LOGICA INTEGRADA: GRAFICO DE EVOLUCION
// =========================================================

function getLinearRegression(dataPoints) {
    const n = dataPoints.length;
    if (n < 2) return null;

    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    let minX = Infinity, maxX = -Infinity;

    dataPoints.forEach(p => {
        sumX += p.x;
        sumY += p.y;
        sumXY += (p.x * p.y);
        sumXX += (p.x * p.x);
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
    });

    const denominator = (n * sumXX - sumX * sumX);
    if (denominator === 0) return null;

    const slope = (n * sumXY - sumX * sumY) / denominator;
    const intercept = (sumY - slope * sumX) / n;

    const startY = slope * minX + intercept;
    const endY = slope * maxX + intercept;

    return {
        slope: slope,
        points: [{x: minX, y: startY}, {x: maxX, y: endY}]
    };
}

// =========================================================
// GRAFICO EVOLUTIVO (CON TENDENCIAS Y PENDIENTES)
// =========================================================

function updateEvolutionChart() {
    const ctx = document.getElementById('evolutionChart').getContext('2d');

    const dataByGame = RAW_SIMULATIONS.filter(row =>
        row.juego === CURRENT_UNIVERSE &&
        row.estado === 'AUDITADO' &&
        row.score !== undefined && row.score !== ""
    );

    if (dataByGame.length === 0) {
        if (evolutionChartInstance) evolutionChartInstance.destroy();
        return;
    }

    const algosRaw = {};
    dataByGame.forEach(row => {
        // --- CAMBIO AQUI: Categorizacion explicita ---
        let algoKey = 'unknown';
        if (row.algoritmo === 'oraculo_neural_v3') algoKey = 'oraculo_neural_v3';
        else if (row.algoritmo === 'oraculo_neural_v4') algoKey = 'oraculo_neural_v4';
        else if (row.algoritmo.includes('forense')) algoKey = 'forense';
        else if (row.algoritmo.includes('gauss')) algoKey = 'gauss';
        else if (row.algoritmo.includes('delta')) algoKey = 'delta';
        else if (row.algoritmo.includes('markov')) algoKey = 'markov';
        else if (row.algoritmo.includes('consenso')) algoKey = 'consenso';

        const target = parseInt(row.objetivo);
        const score = parseFloat(row.score);

        if (!algosRaw[algoKey]) algosRaw[algoKey] = {};
        if (!algosRaw[algoKey][target]) algosRaw[algoKey][target] = [];
        algosRaw[algoKey][target].push(score);
    });

    const algosProcessed = {};
    Object.keys(algosRaw).forEach(key => {
        const targets = Object.keys(algosRaw[key]).map(Number).sort((a,b) => a-b);
        const points = targets.map(t => {
            const scores = algosRaw[key][t];
            const avg = scores.reduce((a,b) => a+b, 0) / scores.length;
            return { x: t, y: avg };
        });

        let label = key.toUpperCase();
        const config = UNIVERSE_CONFIG[CURRENT_UNIVERSE] || UNIVERSE_CONFIG['LOTO'];
        const confAlgo = config.algos.find(a => a.key === key);
        if (confAlgo) label = confAlgo.label;

        algosProcessed[key] = { label: label, points: points, color: confAlgo ? confAlgo.color : '#888' };
    });

    // 3. Generar Datasets
    const datasets = [];

    Object.keys(algosProcessed).forEach(key => {
        const item = algosProcessed[key];

        // Calcular Tendencia
        const regression = getLinearRegression(item.points);
        let labelText = item.label;

        if (regression) {
            const isPositive = regression.slope >= 0;
            // Usamos flechas distintas para mayor claridad visual
            const symbol = isPositive ? "+" : "-";
            const slopeVal = (regression.slope).toFixed(3);

            // La etiqueta lleva la informacion del diagnostico
            // NOTA: Chart.js no permite colores parciales en texto, pero el simbolo ayuda.
            labelText += ` (m:${slopeVal} ${symbol})`;

            // Dataset 1: TENDENCIA (Mantiene el color del algoritmo)
            datasets.push({
                label: `Tendencia ${item.label}`, // Se ocultara en leyenda
                data: regression.points,
                borderColor: item.color, // <--- VOLVEMOS AL COLOR ORIGINAL
                borderWidth: 2,
                borderDash: [4, 4], // Punteado fino
                pointRadius: 0,
                fill: false,
                tension: 0,
                order: 1
            });
        }

        // Dataset 2: DATOS REALES (Curva Suave + Relleno transparente)
        datasets.push({
            label: labelText,
            data: item.points,
            borderColor: item.color,
            backgroundColor: hexToRgba(item.color, 0.1),
            borderWidth: 2,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 6,
            fill: false,
            order: 0
        });
    });

    // 4. Renderizar
    if (evolutionChartInstance) evolutionChartInstance.destroy();

    evolutionChartInstance = new Chart(ctx, {
        type: 'line',
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#c9d1d9',
                        usePointStyle: true,
                        filter: function(item, chart) {
                            // Solo mostramos la etiqueta principal que contiene la pendiente
                            return !item.text.includes('Tendencia');
                        },
                        font: {
                            family: "'JetBrains Mono', monospace", // Fuente mono para alinear numeros
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(22, 27, 34, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#c9d1d9',
                    borderColor: '#30363d',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        title: (ctx) => `Sorteo #${ctx[0].label}`,
                        label: (context) => {
                            if (context.dataset.borderDash && context.dataset.borderDash.length > 0) return null;
                            // Limpiamos la etiqueta para el tooltip (quitamos la pendiente)
                            const cleanLabel = context.dataset.label.split('(')[0].trim();
                            return `${cleanLabel}: ${context.parsed.y.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: { display: true, text: 'N Sorteo', color: '#8b949e' },
                    grid: { color: '#30363d' },
                    ticks: { color: '#8b949e', maxRotation: 0, autoSkip: true }
                },
                y: {
                    title: { display: true, text: 'Afinidad Promedio %', color: '#8b949e' },
                    grid: { color: '#30363d' },
                    ticks: { color: '#8b949e' },
                    beginAtZero: true
                }
            }
        }
    });
}
