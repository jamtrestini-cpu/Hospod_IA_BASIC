import json
import ast
import operator as op
from pathlib import Path

import ollama


# ============================================================
# ⚙️ CONFIGURACIÓN
# ============================================================

MODEL = "llama3.2:3b"

CPU_CORES = 8
RAM_GB = 14

MAX_MEMORY_ITEMS = 1000
MAX_HISTORY = 12

BASE_DIR = Path(__file__).resolve().parent

MEMORY_FILE = BASE_DIR / "aura_memory.json"
CONFIG_FILE = BASE_DIR / "aura_config.json"


# ============================================================
# 🧠 PERSONALIDAD DE AURA
# ============================================================

SYSTEM_PROMPT = """
Tu nombre es AURA.

Eres un asistente personal local creado por el usuario.

Tu objetivo es ayudar con:
- conversación
- programación
- proyectos
- archivos
- aprendizaje
- matemáticas
- ideas
- resolución de problemas

Hablas en español de forma natural.

No respondas como un menú.
No digas "elige una opción" a menos que el usuario lo solicite.

Si el usuario dice "hola", simplemente conversa.

Sé clara, directa y útil.

No inventes información.

Si no sabes algo, dilo.

Cuando tengas recuerdos relevantes del usuario,
utilízalos para personalizar la respuesta.

No menciones los recuerdos internos a menos que sea necesario.
"""


# ============================================================
# 🧠 SISTEMA DE MEMORIA
# ============================================================

class Memory:

    def __init__(self, file_path, max_items=1000):

        self.file_path = file_path
        self.max_items = max_items

        self.items = []

        self.load()


    def load(self):

        if not self.file_path.exists():

            self.items = []

            self.save()

            return

        try:

            data = json.loads(
                self.file_path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(data, list):

                self.items = data

            else:

                self.items = []

        except Exception:

            print("⚠️ No se pudo cargar la memoria.")

            self.items = []


    def save(self):

        try:

            data = self.items[-self.max_items:]

            self.file_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

        except Exception as e:

            print(
                f"⚠️ Error guardando memoria: {e}"
            )


    def add(self, text, kind="permanent"):

        text = text.strip()

        if not text:
            return False

        # Evitar duplicados

        for item in self.items:

            if item.get("text", "").lower() == text.lower():

                return False

        self.items.append(
            {
                "text": text,
                "kind": kind
            }
        )

        # Limitar cantidad

        if len(self.items) > self.max_items:

            self.items = self.items[-self.max_items:]


        self.save()

        return True


    def remove(self, index):

        if index < 0 or index >= len(self.items):

            return False

        self.items.pop(index)

        self.save()

        return True


    def clear(self):

        self.items = []

        self.save()


    def all(self):

        return self.items


    def relevant(self, query, limit=8):

        words = {
            word.lower()
            for word in query.split()
            if len(word) > 2
        }

        results = []

        for item in self.items:

            text = item.get(
                "text",
                ""
            )

            lower_text = text.lower()

            score = 0

            for word in words:

                if word in lower_text:

                    score += 1

            if score > 0:

                results.append(
                    (
                        score,
                        item
                    )
                )


        results.sort(
            key=lambda x: x[0],
            reverse=True
        )


        return [
            item
            for score, item in results[:limit]
        ]


# ============================================================
# 💬 MOTOR DE CHAT
# ============================================================

class ChatEngine:

    def __init__(
        self,
        model,
        system_prompt,
        history_limit=12
    ):

        self.model = model

        self.system_prompt = system_prompt

        self.history = []

        self.history_limit = history_limit


    def clear(self):

        self.history = []


    def build_messages(
        self,
        user_text,
        memories
    ):

        messages = [

            {
                "role": "system",
                "content": self.system_prompt
            }

        ]


        # 🧠 Memoria relevante

        if memories:

            memory_text = "\n".join(
                f"- {item['text']}"
                for item in memories
            )


            messages.append(
                {
                    "role": "system",
                    "content":
                        "Información relevante que recuerdas "
                        "sobre el usuario:\n"
                        + memory_text
                }
            )


        # 💬 Conversación anterior

        messages.extend(
            self.history[-self.history_limit:]
        )


        # 👤 Mensaje actual

        messages.append(
            {
                "role": "user",
                "content": user_text
            }
        )


        return messages


    def chat(
        self,
        user_text,
        memories
    ):

        messages = self.build_messages(
            user_text,
            memories
        )


        try:

            stream = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True
            )


            answer = []


            print(
                "\nAURA: ",
                end="",
                flush=True
            )


            for chunk in stream:

                token = (
                    chunk
                    .get("message", {})
                    .get("content", "")
                )


                if token:

                    print(
                        token,
                        end="",
                        flush=True
                    )

                    answer.append(token)


            print()


            response = "".join(answer)


            # Guardar conversación

            self.history.append(
                {
                    "role": "user",
                    "content": user_text
                }
            )


            self.history.append(
                {
                    "role": "assistant",
                    "content": response
                }
            )


            # Limitar historial

            self.history = (
                self.history[-self.history_limit:]
            )


            return response


        except Exception as e:

            print(
                f"\n❌ Error con Ollama: {e}"
            )

            return ""


# ============================================================
# 🧮 CALCULADORA SEGURA
# ============================================================

OPERATORS = {

    ast.Add: op.add,

    ast.Sub: op.sub,

    ast.Mult: op.mul,

    ast.Div: op.truediv,

    ast.Pow: op.pow,

    ast.Mod: op.mod,

    ast.USub: op.neg

}


def calculate(expression):

    def evaluate(node):

        if isinstance(
            node,
            ast.Constant
        ):

            if isinstance(
                node.value,
                (int, float)
            ):

                return node.value


        if isinstance(
            node,
            ast.UnaryOp
        ):

            operator = OPERATORS.get(
                type(node.op)
            )

            if operator:

                return operator(
                    evaluate(node.operand)
                )


        if isinstance(
            node,
            ast.BinOp
        ):

            operator = OPERATORS.get(
                type(node.op)
            )

            if operator:

                return operator(
                    evaluate(node.left),
                    evaluate(node.right)
                )


        raise ValueError(
            "Operación no permitida."
        )


    tree = ast.parse(
        expression,
        mode="eval"
    )


    return evaluate(
        tree.body
    )


# ============================================================
# 🔀 ROUTER
# ============================================================

def detect_route(text):

    lower = text.lower()


    # Matemáticas

    if lower.startswith(
        "/calcular "
    ):

        return "calculator"


    # Imágenes

    image_words = [

        "imagen",
        "foto",
        "fotografía",
        "captura"

    ]


    if any(
        word in lower
        for word in image_words
    ):

        return "vision"


    # Web

    web_words = [

        "busca en internet",
        "busca en la web",
        "googlea",
        "últimas noticias"

    ]


    if any(
        word in lower
        for word in web_words
    ):

        return "web"


    # Código

    code_words = [

        "código",
        "programa",
        "python",
        "javascript",
        "c++",
        "script",
        "bug",
        "error"

    ]


    if any(
        word in lower
        for word in code_words
    ):

        return "code"


    # Archivos

    file_words = [

        "archivo",
        "pdf",
        "documento",
        "carpeta"

    ]


    if any(
        word in lower
        for word in file_words
    ):

        return "files"


    return "chat"


# ============================================================
# 🧠 AURA
# ============================================================

class Aura:

    def __init__(self):

        self.memory = Memory(
            MEMORY_FILE,
            MAX_MEMORY_ITEMS
        )


        self.chat = ChatEngine(
            MODEL,
            SYSTEM_PROMPT,
            MAX_HISTORY
        )


    # --------------------------------------------------------
    # CONFIGURACIÓN
    # --------------------------------------------------------

    def show_config(self):

        print()

        print("⚙️ CONFIGURACIÓN DE AURA")

        print(
            f"Modelo: {MODEL}"
        )

        print(
            f"CPU configurada: {CPU_CORES} núcleos"
        )

        print(
            f"RAM configurada: {RAM_GB} GB"
        )

        print(
            f"Memorias: {len(self.memory.all())}"
        )

        print()


    # --------------------------------------------------------
    # MEMORIA
    # --------------------------------------------------------

    def show_memory(self):

        memories = self.memory.all()


        if not memories:

            print(
                "\n🧠 AURA todavía no tiene recuerdos."
            )

            return


        print(
            "\n🧠 MEMORIA DE AURA\n"
        )


        for i, item in enumerate(
            memories,
            start=1
        ):

            print(
                f"{i}. {item.get('text', '')}"
            )


        print()


    # --------------------------------------------------------
    # COMANDOS
    # --------------------------------------------------------

    def command(self, text):

        # CONFIG

        if text == "/config":

            self.show_config()

            return True


        # MEMORIA

        if text == "/memoria":

            self.show_memory()

            return True


        # APRENDER

        if text.startswith(
            "/aprender "
        ):

            memory_text = text[
                len("/aprender "):
            ].strip()


            if self.memory.add(
                memory_text
            ):

                print(
                    "\n🧠 AURA aprendió:"
                )

                print(
                    memory_text
                )

            else:

                print(
                    "\n🧠 Esa información "
                    "ya estaba guardada."
                )


            return True


        # LIMPIAR HISTORIAL

        if text == "/limpiar":

            self.chat.clear()

            print(
                "\n🧹 Historial de conversación limpiado."
            )

            return True


        # BORRAR TODA LA MEMORIA

        if text == "/borrar_memoria":

            confirmation = input(
                "¿Borrar toda la memoria? "
                "(si/no): "
            )


            if confirmation.lower() == "si":

                self.memory.clear()

                print(
                    "🧹 Memoria borrada."
                )

            else:

                print(
                    "Operación cancelada."
                )


            return True


        # CALCULADORA

        if text.startswith(
            "/calcular "
        ):

            expression = text[
                len("/calcular "):
            ].strip()


            try:

                result = calculate(
                    expression
                )


                print(
                    f"\n🧮 Resultado: {result}"
                )


            except Exception as e:

                print(
                    f"\n❌ Error: {e}"
                )


            return True


        return False


    # --------------------------------------------------------
    # PROCESAR MENSAJE
    # --------------------------------------------------------


    
    def process(self, text):

        # Comandos

        if self.command(text):

            return


        # Router

        route = detect_route(text)


        # ----------------------------------------------------
        # CHAT NORMAL
        # ----------------------------------------------------

        if route == "chat":

            memories = self.memory.relevant(
                text,
                limit=8
            )


            self.chat.chat(
                text,
                memories
            )


            return


        # ----------------------------------------------------
        # MATEMÁTICAS
        # ----------------------------------------------------

        if route == "calculator":

            self.command(text)

            return


        # ----------------------------------------------------
        # VISIÓN
        # ----------------------------------------------------

        if route == "vision":

            print(
                "\n🖼️ AURA detectó una petición "
                "relacionada con imágenes."
            )

            print(
                "El módulo de visión se conectará "
                "aquí posteriormente."
            )

            return


        # ----------------------------------------------------
        # WEB
        # ----------------------------------------------------

        if route == "web":

            print(
                "\n🌐 AURA detectó que necesitas "
                "información de Internet."
            )

            print(
                "El módulo web se conectará "
                "aquí posteriormente."
            )

            return


        # ----------------------------------------------------
        # CÓDIGO
        # ----------------------------------------------------

        if route == "code":

            memories = self.memory.relevant(
                text,
                limit=8
            )


            self.chat.chat(
                text,
                memories
            )


            return


        # ----------------------------------------------------
        # ARCHIVOS
        # ----------------------------------------------------

        if route == "files":

            print(
                "\n📁 AURA detectó una operación "
                "con archivos."
            )

            print(
                "El módulo de archivos se conectará "
                "aquí posteriormente."
            )

            return


    # --------------------------------------------------------
    # EJECUTAR AURA
    # --------------------------------------------------------

    def run(self):

        print(
            "=" * 60
        )

        print(
            "🧠 AURA V3"
        )

        print(
            "Asistente personal local"
        )

        print(
            "=" * 60
        )

        print(
            f"🤖 Modelo: {MODEL}"
        )

        print(
            f"⚙️ CPU: {CPU_CORES} núcleos"
        )

        print(
            f"💾 RAM configurada: {RAM_GB} GB"
        )

        print(
            f"🧠 Memorias: "
            f"{len(self.memory.all())}"
        )

        print(
            "=" * 60
        )

        print(
            "Comandos:"
        )

        print(
            "/config"
        )

        print(
            "/memoria"
        )

        print(
            "/aprender texto"
        )

        print(
            "/limpiar"
        )

        print(
            "/borrar_memoria"
        )

        print(
            "/calcular 2+2"
        )

        print(
            "Escribe 'salir' para cerrar."
        )

        print(
            "=" * 60
        )


        while True:

            try:

                text = input(
                    "\nTú: "
                ).strip()


            except (
                KeyboardInterrupt,
                EOFError
            ):

                print(
                    "\n\n👋 AURA cerrada."
                )

                break


            if not text:

                continue


            if text.lower() in (
                "salir",
                "exit",
                "quit"
            ):

                print(
                    "\n👋 AURA cerrada."
                )

                break


            self.process(text)


# ============================================================
# 🚀 INICIO
# ============================================================
    def system_command(self, text):

        lower = text.lower().strip()


        # ====================================================
        # LISTAR CARPETA
        # ====================================================

        if lower.startswith("/listar "):

            path = text[len("/listar "):].strip()

            result = list_directory(path)

            if not result["ok"]:

                print(
                    f"\n❌ {result['message']}"
                )

                return


            print(
                f"\n📁 {result['path']}\n"
            )


            for item in result["items"]:

                icon = (
                    "📁"
                    if item["type"] == "CARPETA"
                    else "📄"
                )


                print(
                    f"{icon} {item['name']}"
                )


            return


        # ====================================================
        # INFORMACIÓN
        # ====================================================

        if lower.startswith("/info "):

            path = text[len("/info "):].strip()

            result = file_info(path)

            print()

            if result["ok"]:

                print(
                    f"📄 {result['name']}"
                )

                print(
                    f"📍 {result['path']}"
                )

                print(
                    f"📦 {result['size_bytes']} bytes"
                )


            else:

                print(
                    f"❌ {result['message']}"
                )


            return


        # ====================================================
        # LEER ARCHIVO
        # ====================================================

        if lower.startswith("/leer "):

            path = text[len("/leer "):].strip()

            result = read_file(path)

            print()

            if result["ok"]:

                print(
                    "📖 CONTENIDO:\n"
                )

                print(
                    result["content"]
                )


            else:

                print(
                    f"❌ {result['message']}"
                )


            return


        # ====================================================
        # CREAR CARPETA
        # ====================================================

        if lower.startswith("/crear_carpeta "):

            path = text[
                len("/crear_carpeta "):
            ].strip()


            result = create_directory(path)

            print(
                result["message"]
            )


            return


        # ====================================================
        # ELIMINAR
        # ====================================================

        if lower.startswith("/eliminar "):

            path = text[
                len("/eliminar "):
            ].strip()


            # Primera comprobación

            result = delete_path(
                path,
                confirmed=False
            )


            if result.get(
                "requires_confirmation"
            ):

                print()
                print(
                    result["message"]
                )

                print()


                confirmation = input(
                    "¿Quieres que AURA lo elimine? "
                    "Escribe CONFIRMAR: "
                )


                if confirmation == "CONFIRMAR":

                    result = delete_path(
                        path,
                        confirmed=True
                    )


                    print(
                        result["message"]
                    )


                else:

                    print(
                        "🛡️ Operación cancelada."
                    )


                return


            print(
                result["message"]
            )

            return


        return False




if __name__ == "__main__":

    aura = Aura()

    aura.run()