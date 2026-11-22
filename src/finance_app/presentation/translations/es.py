"""Spanish UI catalog. Keys are the English source strings (placeholders must match)."""

from __future__ import annotations

SPANISH: dict[str, str] = {
    # --- Main window ---
    "Investment Simulator & Portfolio Tracker": "Simulador de inversiones y seguimiento de cartera",
    "Simulator": "Simulador",
    "Portfolio": "Cartera",
    "&Language": "&Idioma",
    "Something went wrong": "Algo ha salido mal",
    "Storage: Google Sheets": "Almacenamiento: Google Sheets",
    "Storage: custom repository": "Almacenamiento: repositorio personalizado",
    "Offline": "Sin conexión",
    "Offline mode: investments are kept in memory only. Configure Google Sheets "
    "in {path} to persist them (see README).": (
        "Modo sin conexión: las inversiones solo se guardan en memoria. Configura Google "
        "Sheets en {path} para conservarlas (consulta el README)."
    ),
    "Google Sheets unavailable ({error}). Running offline: data will not be saved.": (
        "Google Sheets no está disponible ({error}). Modo sin conexión: los datos no se guardarán."
    ),
    "<b>Disclaimer:</b> this is a simulation for informational and educational purposes only. "
    "It is not financial or tax advice. Projected returns are hypothetical, and past "
    "performance does not guarantee future results. Tax rules can change; check them with a "
    "qualified advisor.": (
        "<b>Aviso legal:</b> esto es una simulación con fines exclusivamente informativos y "
        "educativos. No constituye asesoramiento financiero ni fiscal. Las rentabilidades "
        "proyectadas son hipotéticas y las rentabilidades pasadas no garantizan resultados "
        "futuros. La normativa fiscal puede cambiar; consúltala con un asesor cualificado."
    ),
    # --- Formatting ---
    "{n} year": "{n} año",
    "{n} years": "{n} años",
    "{n} month": "{n} mes",
    "{n} months": "{n} meses",
    # --- Options ---
    "Daily": "Diaria",
    "Monthly": "Mensual",
    "Quarterly": "Trimestral",
    "Semiannual": "Semestral",
    "Annual": "Anual",
    "Beginning of period": "Al inicio del periodo",
    "End of period": "Al final del periodo",
    "Years": "Años",
    "Months": "Meses",
    " yrs": " años",
    # --- Simulator inputs ---
    "Basic": "Básico",
    "Advanced": "Avanzado",
    "Initial capital": "Capital inicial",
    "Periodic contribution": "Aportación periódica",
    "Amount added every period (can be zero).": "Importe aportado cada periodo (puede ser cero).",
    "Contribution frequency": "Frecuencia de aportación",
    "Expected annual return": "Rentabilidad anual esperada",
    "Nominal annual rate before fees.": "Tipo anual nominal antes de comisiones.",
    "Time horizon": "Horizonte temporal",
    "Compounding": "Capitalización",
    "How often interest is reinvested.": "Con qué frecuencia se reinvierten los intereses.",
    "Contribution timing": "Momento de la aportación",
    "Contributions at the beginning of the period earn interest for that period.": (
        "Las aportaciones al inicio del periodo generan intereses durante ese periodo."
    ),
    "Annual contribution increase": "Incremento anual de la aportación",
    "Estimated inflation": "Inflación estimada",
    "Used to compute the real value (purchasing power).": (
        "Se usa para calcular el valor real (poder adquisitivo)."
    ),
    "Annual fees (TER)": "Comisiones anuales (TER)",
    "Total expense ratio charged on the balance.": "Gastos corrientes cobrados sobre el saldo.",
    "Apply Spanish savings tax to gains": "Aplicar el IRPF del ahorro a las ganancias",
    "Progressive savings-income brackets (19–30 %) applied to realised gains on "
    "withdrawals and to the remaining gains when liquidating at the end. "
    "Yearly dividend taxation is not modelled.": (
        "Tramos progresivos de la base del ahorro (19–30 %) aplicados a las ganancias "
        "realizadas en los reembolsos y a las ganancias restantes al liquidar al final. "
        "No se modela la tributación anual de dividendos."
    ),
    "<b>Withdrawals</b> (retirement phase, set amount to 0 to disable)": (
        "<b>Retiradas</b> (fase de jubilación; importe 0 para desactivarlas)"
    ),
    "Withdrawal amount": "Importe de la retirada",
    "Withdrawal frequency": "Frecuencia de retirada",
    "Start withdrawals after": "Empezar retiradas tras",
    "Contributions stop when withdrawals start.": (
        "Las aportaciones se detienen cuando empiezan las retiradas."
    ),
    # --- Results ---
    "Final capital": "Capital final",
    "Total accumulated at the end of the horizon (before tax).": (
        "Total acumulado al final del horizonte (antes de impuestos)."
    ),
    "Total contributed": "Total aportado",
    "Money invested from your own pocket.": "Dinero invertido de tu propio bolsillo.",
    "Interest earned": "Intereses generados",
    "Final capital + withdrawals − contributions (net of fees): the compounding effect.": (
        "Capital final + retiradas − aportaciones (neto de comisiones): el efecto del "
        "interés compuesto."
    ),
    "Inflation-adjusted value": "Valor ajustado por inflación",
    "Final capital in today's money.": "Capital final en dinero de hoy.",
    "Final capital after tax": "Capital final tras impuestos",
    "If fully liquidated at the end.": "Si se liquida por completo al final.",
    "Total return": "Rentabilidad total",
    "Interest earned / total contributed.": "Intereses generados / total aportado.",
    "Equivalent annual rate (IRR)": "Tasa anual equivalente (TIR)",
    "Money-weighted annual return of all cash flows (before / after tax).": (
        "Rentabilidad anual ponderada por capital de todos los flujos (antes / después de "
        "impuestos)."
    ),
    "Fees & taxes": "Comisiones e impuestos",
    "Total fees (TER) and taxes paid or due.": (
        "Total de comisiones (TER) e impuestos pagados o pendientes."
    ),
    "Withdrawn: {value}": "Retirado: {value}",
    "After tax: {value}": "Tras impuestos: {value}",
    "Depleted after {duration}": "Agotado tras {duration}",
    "Fees {fees} · Taxes {taxes}": "Comisiones {fees} · Impuestos {taxes}",
    # --- Simulator view / charts / table ---
    "Save as investment…": "Guardar como inversión…",
    "Track this plan in the Portfolio tab": "Seguir este plan en la pestaña Cartera",
    "Growth chart": "Gráfico de crecimiento",
    "Breakdown table": "Tabla de desglose",
    "Scenarios": "Escenarios",
    "Fix the highlighted inputs to update the results.": (
        "Corrige los campos marcados para actualizar los resultados."
    ),
    "Growth: contributed capital vs. interest (year end)": (
        "Crecimiento: capital aportado frente a intereses (fin de año)"
    ),
    "Contributed capital": "Capital aportado",
    "Interest": "Intereses",
    "Year": "Año",
    "Month": "Mes",
    "Year {year}: {value}": "Año {year}: {value}",
    "Year {year}\nContributed: {contributed}\nInterest: {interest}\nBalance: {balance}": (
        "Año {year}\nAportado: {contributed}\nIntereses: {interest}\nSaldo: {balance}"
    ),
    "Opening balance": "Saldo inicial",
    "Contributions": "Aportaciones",
    "Fees": "Comisiones",
    "Withdrawals": "Retiradas",
    "Taxes": "Impuestos",
    "Closing balance": "Saldo final",
    "Real value": "Valor real",
    "Yearly": "Anual",
    "View:": "Vista:",
    "Scenario comparison (balance at year end)": ("Comparación de escenarios (saldo a fin de año)"),
    "Scenario": "Escenario",
    "Annual return": "Rentabilidad anual",
    "After tax": "Tras impuestos",
    "IRR": "TIR",
    "Pessimistic": "Pesimista",
    "Baseline": "Base",
    "Optimistic": "Optimista",
    # --- Portfolio ---
    "Investments": "Inversiones",
    "Refresh": "Actualizar",
    "Delete investment": "Eliminar inversión",
    "No investments yet.\n\nConfigure a plan in the Simulator tab and click "
    "“Save as investment…” to start tracking it here.": (
        "Todavía no hay inversiones.\n\nConfigura un plan en la pestaña Simulador y pulsa "
        "«Guardar como inversión…» para empezar a seguirlo aquí."
    ),
    "Select an investment to see its performance.": (
        "Selecciona una inversión para ver su evolución."
    ),
    "Confirm": "Confirmar",
    "Delete the snapshot of {date}?": "¿Eliminar el registro del {date}?",
    "Delete “{name}” and all its snapshots? This cannot be undone.": (
        "¿Eliminar «{name}» y todos sus registros? Esta acción no se puede deshacer."
    ),
    "Name": "Nombre",
    "Start": "Inicio",
    "Expected": "Esperada",
    "Latest value": "Último valor",
    "Deviation": "Desviación",
    "Performance": "Evolución",
    " (closed)": " (cerrada)",
    "No data yet": "Sin datos todavía",
    "Ahead of plan": "Por encima del plan",
    "On track": "Según el plan",
    "Behind plan": "Por debajo del plan",
    "Active": "Activa",
    "Closed": "Cerrada",
    "Expected annual rate": "Tasa anual esperada",
    "Money-weighted rate of the original projection.": (
        "Tasa ponderada por capital de la proyección original."
    ),
    "Actual annual rate (XIRR)": "Tasa anual real (TIR.NO.PER)",
    "Money-weighted return of your real cash flows.": (
        "Rentabilidad ponderada por capital de tus flujos reales."
    ),
    "Projected at last snapshot": "Proyectado en el último registro",
    "Actual value": "Valor real actual",
    "Actual − projected at the latest snapshot.": "Real − proyectado en el último registro.",
    "Status": "Estado",
    "Within ±tolerance of the plan counts as on track.": (
        "Dentro de ±tolerancia respecto al plan se considera según el plan."
    ),
    "Projected final capital": "Capital final proyectado",
    "Plan": "Plan",
    "Date": "Fecha",
    "Market value": "Valor de mercado",
    "Contributed": "Aportado",
    "Withdrawn": "Retirado",
    "Projected": "Proyectado",
    "Deviation %": "Desviación %",
    "Note": "Nota",
    "Show full horizon": "Mostrar horizonte completo",
    "Add snapshot…": "Añadir registro…",
    "Edit": "Editar",
    "Delete": "Eliminar",
    "Open in simulator": "Abrir en el simulador",
    "Close investment": "Cerrar inversión",
    "Reopen investment": "Reabrir inversión",
    "<b>Performance snapshots</b>": "<b>Registros de evolución</b>",
    "{n} snapshot(s)": "{n} registro(s)",
    "Started {start} · {initial} initial · {contribution} {frequency} · "
    "{rate} expected · {horizon}": (
        "Inicio {start} · {initial} iniciales · {contribution} {frequency} · "
        "{rate} esperado · {horizon}"
    ),
    "Projected vs. actual performance": "Evolución proyectada frente a real",
    "Projected balance": "Saldo proyectado",
    "Projected contributions": "Aportaciones proyectadas",
    "Actual contributions": "Aportaciones reales",
    "Snapshots": "Registros",
    # --- Dialogs ---
    "Save as investment": "Guardar como inversión",
    "e.g. MSCI World index fund": "p. ej., fondo indexado MSCI World",
    "Start date": "Fecha de inicio",
    "Notes": "Notas",
    "Enter a name for the investment.": "Introduce un nombre para la inversión.",
    "Edit snapshot": "Editar registro",
    "Add performance snapshot": "Añadir registro de evolución",
    "Current market value": "Valor de mercado actual",
    "Contributed since last snapshot": "Aportado desde el último registro",
    "Withdrawn since last snapshot": "Retirado desde el último registro",
    "Enter the current market value (must be greater than zero).": (
        "Introduce el valor de mercado actual (debe ser mayor que cero)."
    ),
    "The date cannot be before the investment start date.": (
        "La fecha no puede ser anterior a la fecha de inicio de la inversión."
    ),
    # --- Portfolio messages ---
    "Investment “{name}” saved.": "Inversión «{name}» guardada.",
    "Snapshot saved.": "Registro guardado.",
    "Snapshot deleted.": "Registro eliminado.",
    "Investment updated.": "Inversión actualizada.",
    "Investment deleted.": "Inversión eliminada.",
    # --- Domain / application validation messages ---
    "Time horizon must be between 1 month and 100 years.": (
        "El horizonte temporal debe estar entre 1 mes y 100 años."
    ),
    "Withdrawal amount must be greater than zero.": (
        "El importe de la retirada debe ser mayor que cero."
    ),
    "Unsupported withdrawal frequency.": "Frecuencia de retirada no admitida.",
    "Withdrawal start cannot be negative.": "El inicio de las retiradas no puede ser negativo.",
    "Initial capital cannot be negative.": "El capital inicial no puede ser negativo.",
    "Periodic contribution cannot be negative.": "La aportación periódica no puede ser negativa.",
    "Unsupported contribution frequency.": "Frecuencia de aportación no admitida.",
    "Annual return must be between -50 % and 100 %.": (
        "La rentabilidad anual debe estar entre -50 % y 100 %."
    ),
    "Inflation must be between 0 % and 50 %.": "La inflación debe estar entre 0 % y 50 %.",
    "Fees (TER) must be between 0 % and 10 %.": (
        "Las comisiones (TER) deben estar entre 0 % y 10 %."
    ),
    "Contribution increase must be between 0 % and 50 %.": (
        "El incremento de la aportación debe estar entre 0 % y 50 %."
    ),
    "Enter an initial capital or a periodic contribution.": (
        "Introduce un capital inicial o una aportación periódica."
    ),
    "Withdrawals must start before the end of the time horizon.": (
        "Las retiradas deben empezar antes del final del horizonte temporal."
    ),
    "Withdrawal amount cannot be negative.": "El importe de la retirada no puede ser negativo.",
    "Name cannot be empty.": "El nombre no puede estar vacío.",
    "Name must be at most 100 characters.": "El nombre no puede superar los 100 caracteres.",
    "Snapshot date cannot be before the investment start date.": (
        "La fecha del registro no puede ser anterior al inicio de la inversión."
    ),
    "A snapshot already exists for that date.": "Ya existe un registro para esa fecha.",
    "Market value cannot be negative.": "El valor de mercado no puede ser negativo.",
    "Contribution cannot be negative.": "La aportación no puede ser negativa.",
    "Withdrawal cannot be negative.": "La retirada no puede ser negativa.",
    "Last bracket must have no upper limit.": "El último tramo no debe tener límite superior.",
    "Bracket limits must be ascending.": "Los límites de los tramos deben ser ascendentes.",
    "Tax rates must be between 0 and 1.": "Los tipos impositivos deben estar entre 0 y 1.",
    # --- Budgeting ---
    "Finance manager": "Gestor de finanzas",
    "Budget": "Presupuesto",
    "Transactions": "Movimientos",
    "Categories": "Categorías",
    "Offline mode: data is kept in memory only. Configure Google Sheets "
    "in {path} to persist it (see README).": (
        "Modo sin conexión: los datos solo se guardan en memoria. Configura Google "
        "Sheets en {path} para conservarlos (consulta el README)."
    ),
    # Months
    "January": "Enero",
    "February": "Febrero",
    "March": "Marzo",
    "April": "Abril",
    "May": "Mayo",
    "June": "Junio",
    "July": "Julio",
    "August": "Agosto",
    "September": "Septiembre",
    "October": "Octubre",
    "November": "Noviembre",
    "December": "Diciembre",
    "{month} {year}": "{month} de {year}",
    "{month}: {value}": "{month}: {value}",
    # Kinds and statuses
    "Income": "Ingreso",
    "Expense": "Gasto",
    "Type": "Tipo",
    "All": "Todos",
    "Favorable": "Favorable",
    "On budget": "Dentro del presupuesto",
    "Unfavorable": "Desfavorable",
    # Category manager
    "Add category": "Añadir categoría",
    "Edit category": "Editar categoría",
    "Add income category": "Añadir categoría de ingreso",
    "Add expense category": "Añadir categoría de gasto",
    "Income categories": "Categorías de ingresos",
    "Expense categories": "Categorías de gastos",
    "Add default categories": "Añadir categorías predeterminadas",
    "No categories yet.": "Aún no hay categorías.",
    "State": "Estado",
    "Category": "Categoría",
    "Description": "Descripción",
    "Amount": "Importe",
    "Archived": "Archivada",
    "Archive": "Archivar",
    "Unarchive": "Desarchivar",
    "Rename": "Renombrar",
    "Delete the category “{name}”?": "¿Eliminar la categoría «{name}»?",
    "Used by budgets or transactions; archive it instead.": (
        "La usan presupuestos o movimientos; archívala en su lugar."
    ),
    "The type cannot change once the category is in use.": (
        "El tipo no se puede cambiar una vez que la categoría está en uso."
    ),
    "Enter a name for the category.": "Introduce un nombre para la categoría.",
    # Default categories
    "Salary": "Nómina",
    "Freelance work": "Trabajo freelance",
    "Other income": "Otros ingresos",
    "Housing": "Vivienda",
    "Utilities": "Suministros",
    "Groceries": "Compra",
    "Transport": "Transporte",
    "Health": "Salud",
    "Leisure": "Ocio",
    "Savings": "Ahorro",
    "Other expenses": "Otros gastos",
    # Monthly budget
    "Create budget": "Crear presupuesto",
    "Copy from another month…": "Copiar de otro mes…",
    "Copy budget from another month": "Copiar presupuesto de otro mes",
    "Copy from": "Copiar de",
    "There is no other budget to copy.": "No hay ningún otro presupuesto que copiar.",
    "Delete budget": "Eliminar presupuesto",
    "No budget for {month} {year}.\n\nCreate one or copy an existing month's budget.": (
        "No hay presupuesto para {month} de {year}.\n\nCrea uno o copia el presupuesto de otro mes."
    ),
    "Planned expenses": "Gastos previstos",
    "Planned income": "Ingresos previstos",
    "Add line": "Añadir línea",
    "Edit line": "Editar línea",
    "Delete line": "Eliminar línea",
    "Add budget line": "Añadir línea de presupuesto",
    "Edit budget line": "Editar línea de presupuesto",
    "Delete this budget line?": "¿Eliminar esta línea de presupuesto?",
    "Total expenses: {total}": "Gastos totales: {total}",
    "Total income: {total}": "Ingresos totales: {total}",
    "Notes for this month's budget": "Notas del presupuesto de este mes",
    "Save notes": "Guardar notas",
    "Expected amount": "Importe previsto",
    "Enter an expected amount greater than zero.": (
        "Introduce un importe previsto mayor que cero."
    ),
    "Create a category first (Budget → Categories tab).": (
        "Crea primero una categoría (pestaña Presupuesto → Categorías)."
    ),
    "Delete the budget of {month} {year} and all its lines? This cannot be undone.": (
        "¿Eliminar el presupuesto de {month} de {year} y todas sus líneas? "
        "Esta acción no se puede deshacer."
    ),
    # Variance and charts
    "Variance by category": "Desviación por categoría",
    "Variance": "Desviación",
    "Variance %": "Desviación %",
    "vs. plan: {diff}": "frente a lo previsto: {diff}",
    "Actual income": "Ingresos reales",
    "Actual expenses": "Gastos reales",
    "Planned net": "Neto previsto",
    "Actual net": "Neto real",
    "Planned income minus planned expenses.": "Ingresos previstos menos gastos previstos.",
    "Actual income minus actual expenses.": "Ingresos reales menos gastos reales.",
    "Planned vs. actual": "Previsto frente a real",
    "Expense breakdown": "Desglose de gastos",
    "Planned": "Previsto",
    "Actual": "Real",
    "{name}\nPlanned: {planned}\nActual: {actual}\nVariance: {variance}": (
        "{name}\nPrevisto: {planned}\nReal: {actual}\nDesviación: {variance}"
    ),
    # Annual view
    " (no budget)": " (sin presupuesto)",
    "Double-click a month to open it in the Monthly tab.": (
        "Haz doble clic en un mes para abrirlo en la pestaña Mensual."
    ),
    # Transactions
    "Add entry": "Añadir movimiento",
    "Edit entry": "Editar movimiento",
    "No entries for this month.": "No hay movimientos en este mes.",
    "Show:": "Mostrar:",
    "Enter an amount greater than zero.": "Introduce un importe mayor que cero.",
    "Income: {income} · Expenses: {expenses} · Net: {net}": (
        "Ingresos: {income} · Gastos: {expenses} · Neto: {net}"
    ),
    "Delete the {kind} of {amount} on {date}?": (
        "¿Eliminar el movimiento ({kind}) de {amount} del {date}?"
    ),
    # Messages and domain validation
    "Budget created.": "Presupuesto creado.",
    "Budget updated.": "Presupuesto actualizado.",
    "Budget deleted.": "Presupuesto eliminado.",
    "Budget line saved.": "Línea de presupuesto guardada.",
    "Budget line deleted.": "Línea de presupuesto eliminada.",
    "Category “{name}” created.": "Categoría «{name}» creada.",
    "Category updated.": "Categoría actualizada.",
    "Category deleted.": "Categoría eliminada.",
    "Default categories created.": "Categorías predeterminadas creadas.",
    "Transaction saved.": "Movimiento guardado.",
    "Transaction deleted.": "Movimiento eliminado.",
    "A budget already exists for that month.": "Ya existe un presupuesto para ese mes.",
    "A category with this name already exists for this type.": (
        "Ya existe una categoría con este nombre para este tipo."
    ),
    "Category is used by budgets or transactions and cannot be deleted.": (
        "La categoría está en uso en presupuestos o movimientos y no se puede eliminar."
    ),
    "This category is archived.": "Esta categoría está archivada.",
    "Select a category.": "Selecciona una categoría.",
    "Amount must be greater than zero.": "El importe debe ser mayor que cero.",
    "Category name cannot be empty.": "El nombre de la categoría no puede estar vacío.",
    "Category name must be at most 60 characters.": (
        "El nombre de la categoría no puede superar los 60 caracteres."
    ),
    "Description must be at most 200 characters.": (
        "La descripción no puede superar los 200 caracteres."
    ),
    "Notes must be at most 2000 characters.": "Las notas no pueden superar los 2000 caracteres.",
    "Year must be between 1900 and 2200.": "El año debe estar entre 1900 y 2200.",
    "Month must be between 1 and 12.": "El mes debe estar entre 1 y 12.",
}
