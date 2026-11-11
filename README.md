# HSG SGMI – Prototipo del Sprint 1 (MVP)

Prototipo web del Sistema de Gestión de Medicamentos Intranet del Hospital San Gabriel.
Corre en tu computador (localhost) con **Python (Flask)**, **MySQL**, **HTML** y **CSS** (con modo claro y oscuro).

## 1. Requisitos
- Python 3.10 o superior
- MySQL 8 encendido en tu computador

## 2. Instalación
```
cd hsg_sgmi
python -m venv venv
venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (Mac / Linux)
pip install -r requirements.txt
```

## 3. Clave de MySQL
Si tu usuario `root` tiene clave, indícala antes de iniciar:
```
set DB_PASSWORD=tu_clave        (Windows CMD)
$env:DB_PASSWORD="tu_clave"     (Windows PowerShell)
export DB_PASSWORD=tu_clave     (Mac / Linux)
```
Opcionales: `DB_HOST` (localhost), `DB_PORT` (3306) y `DB_USER` (root).

## 4. Crear la base de datos y ejecutar
```
python init_db.py      # crea la base hsg_sgmi, las tablas y datos de ejemplo
python app.py          # inicia el servidor
```
Abre http://localhost:5000

`init_db.py` borra y vuelve a crear las tablas: úsalo para reiniciar los datos de prueba.

## 5. Usuarios de prueba
| Perfil | Usuario | Clave |
|---|---|---|
| Personal de Bodega | bodega1 | Bodega123 |
| Personal de Área Clínica (Urgencias) | urgencias1 | Clinica123 |
| Personal de Área Clínica (Pabellón) | pabellon1 | Clinica123 |
| Personal de Farmacia | farmacia1 | Farmacia123 |
| Personal de Gerencia | gerencia1 | Gerencia123 |

## 6. Qué incluye (historias del Sprint 1)
| Historia | Pantalla | Perfil |
|---|---|---|
| HU-1 Registro de entradas | Registrar entradas + comprobante con ID único | Bodega |
| HU-2 Cuarentena | Inventario y cuarentena (motivo obligatorio, liberar lote) | Bodega |
| HU-3 Solicitud digital por paciente | Nueva solicitud | Área Clínica |
| HU-4 Estado de solicitudes | Solicitudes (se actualiza cada 15 s, cancelar pendientes) | Clínica, Farmacia, Gerencia |
| HU-5 Despacho con FEFO | Solicitudes: preparar, despachar, rechazar con motivo | Farmacia |
| HU-6 Alertas de stock mínimo | Alertas de stock (crítico / mínimo / seguridad) | Farmacia, Gerencia |
| HU-7 Semáforo de vencimientos | Vencimientos | Bodega, Farmacia, Gerencia |
| Login y perfiles | Ingreso con permisos por perfil | Todos |
| Interfaz | Responsive, accesible (WCAG 2.0 AA como objetivo), modo claro / oscuro | Todos |

## 7. Decisiones del prototipo
- **Semáforo (HU-7):** rojo = 30 días o menos, amarillo = 31 a 60, verde = más de 60, y "Vencido" aparte. Así no queda un rango sin color (el criterio original dejaba sin definir de 60 a 90 días).
- **FEFO:** el despacho toma primero el lote que vence antes y nunca usa lotes vencidos ni en cuarentena. Si no alcanza el stock, despacha parcial y lo informa.
- **Stock vigente (alertas):** suma solo lotes Disponibles y no vencidos.
- **Seguridad básica:** claves con hash, permisos por perfil y token CSRF en los formularios.

## 8. Pendiente (Sprint 2 y siguientes)
Trazabilidad MINSAL (HU-8), integración con el HIS (HU-9), KPI de pérdidas (HU-10), envío de alertas por correo, HTTPS, y verificación formal de WCAG 2.0.

## 9. Estructura
```
hsg_sgmi/
├── app.py            rutas y permisos (Flask)
├── funciones.py      funciones de negocio (Python + SQL)
├── db.py             conexión a MySQL
├── init_db.py        crea la base y carga datos de ejemplo
├── schema.sql        tablas de MySQL
├── templates/        páginas HTML
└── static/
    ├── css/estilos.css   estilos y modo claro / oscuro
    └── js/tema.js        botón de tema
```
