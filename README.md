# 🧠 Notion KaTeX Renderer

Este proyecto convierte automáticamente las ecuaciones escritas en formato **LaTeX** (`$...$` o `$$...$$`) dentro de las páginas de **Notion** en bloques de ecuación renderizados correctamente mediante la **API oficial de Notion**.

Está desarrollado en **Python** y utiliza la librería `notion-client` para conectarse a la API, junto con `dotenv` para gestionar las credenciales de forma segura.

---

## 📘 Descripción general

Cuando escribes ecuaciones en Notion usando el formato `$E = mc^2$`, Notion no las interpreta automáticamente como ecuaciones matemáticas renderizadas.  
Este script se encarga de recorrer todos los bloques de texto de una página (y sus subbloques), detectar expresiones LaTeX, y reemplazarlas por **bloques nativos de ecuación** en Notion, logrando una visualización profesional y limpia.

---

## ⚙️ Requisitos previos

Antes de ejecutar el script, necesitas:

1. **Python 3.8 o superior**
2. **Una integración en Notion** con permisos de lectura y escritura  
   (creada desde [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations))
3. **El ID de la página de Notion** que deseas procesar.

---

## 📦 Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tuusuario/notion-katex-renderer.git
   cd notion-katex-renderer


2. Instala las dependencias necesarias:

   ```bash
   pip install -r requirements.txt
   ```

3. Crea un archivo `.env` en la raíz del proyecto con tu **API key de Notion** y el **ID de la página** que quieres procesar:

   ```bash
   NOTION_API_KEY=secret_tu_api_key_aqui
   PAGE_ID_TO_PROCESS=tu_page_id_aqui
   ```

💡 **Tip:**
Puedes duplicar el archivo `.env.example` incluido en el repositorio y renombrarlo a `.env`.

---

## ▶️ Ejecución

Una vez configurado el entorno, ejecuta:

```bash
python src/main.py
```

El script comenzará a recorrer todos los bloques de texto de la página indicada en `PAGE_ID_TO_PROCESS`.
Detectará ecuaciones escritas en formato:

* `$x^2 + y^2 = z^2$` → ecuaciones **inline**
* `$$E = mc^2$$` → ecuaciones **en bloque**

Y las reemplazará por bloques de tipo `equation` nativos de Notion, que se renderizan automáticamente con KaTeX.

---

## 🔍 Cómo funciona internamente

1. **Carga del entorno y conexión a Notion**

   * Se leen las variables del archivo `.env`
   * Se inicializa el cliente de Notion con tu API key

2. **Recorrido de la página**

   * El script obtiene todos los bloques hijos de la página usando `notion.blocks.children.list`
   * Recorre recursivamente subbloques (listas, toggles, tablas, etc.)

3. **Detección de expresiones LaTeX**

   * Se usan expresiones regulares para buscar texto entre `$...$` o `$$...$$`
   * Por ejemplo:

     * `$a^2 + b^2 = c^2$` → ecuación inline
     * `$$E = mc^2$$` → ecuación en bloque

4. **Reemplazo por bloques de ecuación**

   * Si se encuentra una ecuación:

     * Se crea un nuevo bloque de tipo `equation`
     * Se inserta después del bloque original
     * Se elimina el bloque antiguo para no duplicar contenido

5. **Registro de progreso**

   * El script imprime en consola los bloques modificados y las ecuaciones detectadas.

---

## 🧱 Ejemplo práctico

Supongamos que tienes en Notion este texto:

```
La ecuación de Einstein es $$E = mc^2$$ y el teorema de Pitágoras es $a^2 + b^2 = c^2$.
```

Después de ejecutar el script, el resultado será:

* Un bloque de texto con “La ecuación de Einstein es”
* Un bloque de ecuación con `E = mc^2`
* Otro bloque de texto con “y el teorema de Pitágoras es”
* Un bloque de ecuación con `a^2 + b^2 = c^2`

Todo renderizado con el estilo visual nativo de Notion ✅

---

## ⚠️ Precauciones

* Este script **modifica directamente** los bloques en la página de Notion.
* Se recomienda **crear una copia de la página original** antes de procesarla.
* No compartas nunca tu `NOTION_API_KEY` ni subas tu `.env` a GitHub.

---

## 🧩 Estructura del proyecto

```
notion-katex-renderer/
│
├── src/
│   └── main.py               # Script principal con la lógica de procesamiento
│
├── .env.example              # Plantilla de variables de entorno
├── requirements.txt          # Dependencias del proyecto
├── README.md                 # Este archivo
└── .gitignore                # Archivos que no se suben al repositorio
```

---

## 🔮 Próximas mejoras

* [ ] Añadir barra de progreso o logging visual
* [ ] Guardar copia de seguridad de los bloques antes de modificarlos
* [ ] Crear una **interfaz gráfica** o **CLI interactiva**
* [ ] Implementar una **extensión de Chrome** para renderizado en tiempo real

---

## 🪪 Licencia

Este proyecto se distribuye bajo la licencia **MIT**.
Hecho  por [Daniel Rúa].

---

## 🧩 Créditos

* API oficial de Notion: [https://developers.notion.com](https://developers.notion.com)
* Motor de renderizado KaTeX: [https://katex.org](https://katex.org)

```

---


