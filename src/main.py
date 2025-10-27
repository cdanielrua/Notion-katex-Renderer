import os
import re
from notion_client import Client
import time

# --- Configuración --- 
from dotenv import load_dotenv
import os

load_dotenv()  # Carga las variables desde .env

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
PAGE_ID_TO_PROCESS = os.getenv("PAGE_ID_TO_PROCESS")


TEXT_BEARING_BLOCK_TYPES = [
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item",
    "to_do", "toggle", "quote", "callout"
]
RECURSIVE_CHILD_BEARING_TYPES = [
    "bulleted_list_item", "numbered_list_item", "to_do", "toggle"
]

# --- Funciones Auxiliares (las mismas que antes, asegúrate de que estén completas) ---
def get_plain_text_from_rich_text(rich_text_list):
    if rich_text_list is None: return ""
    return "".join([rt.get("plain_text", "") for rt in rich_text_list])

def parse_text_for_inline_katex(text: str):
    parts = re.split(r'(\$(?!\$)[^$]*?\$(?<!\$\$))', text) 
    if len(parts) == 1: return None
    segments = []
    has_katex_segment = False
    for part_content in parts:
        if not part_content: continue
        is_inline_katex = part_content.startswith("$") and part_content.endswith("$") and \
                          not part_content.startswith("$$") and not part_content.endswith("$$") and \
                          len(part_content) > 2 
        if is_inline_katex:
            expression = part_content[1:-1].strip()
            if expression: 
                segments.append(('katex', expression))
                has_katex_segment = True
        else:
            if part_content or (segments and segments[-1][0] == 'katex'):
                 segments.append(('text', part_content))
    return segments if has_katex_segment and not all(s[0] == 'text' for s in segments) else None

def create_equation_block_payload(katex_expression: str):
    return {"object": "block", "type": "equation", "equation": {"expression": katex_expression}}

def create_paragraph_block_payload_from_rich_text_list(rich_text_list: list):
    if not rich_text_list or not any(rt.get("text", {}).get("content", "").strip() or rt.get("type") == "equation" for rt in rich_text_list):
        return None
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text_list}}

def create_paragraph_block_payload_from_plain_text(plain_text: str):
    stripped_plain_text = plain_text.strip()
    if not stripped_plain_text: return None
    return {"object": "block", "type": "paragraph", 
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": stripped_plain_text}}]}}

def get_rich_text_list_from_block_data(block_data):
    block_type = block_data.get("type")
    if block_type in TEXT_BEARING_BLOCK_TYPES:
        type_specific_data = block_data.get(block_type, {})
        return type_specific_data.get("rich_text")
    return None

def process_simple_table_rows(table_block_id: str, depth: int, notion_client: Client):
    # (Esta función se mantiene igual que la última versión que te di)
    # ... (código de process_simple_table_rows de la respuesta anterior) ...
    # Asegúrate de que esta función esté completa aquí.
    indent = "  " * depth
    print(f"{indent}DEBUG (Tabla): Procesando filas de la tabla ID: {table_block_id}")
    table_rows_children = []
    next_cursor = None
    try:
        while True:
            response = notion_client.blocks.children.list(block_id=table_block_id, start_cursor=next_cursor, page_size=100)
            table_rows_children.extend(response.get("results", []))
            next_cursor = response.get("next_cursor")
            if not next_cursor: break
    except Exception as e:
            print(f"{indent}DEBUG (Tabla): ERROR obteniendo filas para la tabla {table_block_id}: {e}"); return
    for row_block in table_rows_children:
        if row_block.get("type") == 'table_row':
            row_id = row_block["id"]; original_cells_data = row_block.get('table_row', {}).get('cells', [])
            new_cells_data_for_row = []; row_was_modified = False
            print(f"{indent}DEBUG (Tabla):   Procesando Fila ID: {row_id}. Celdas: {len(original_cells_data)}")
            for cell_index, cell_rich_text_list_original in enumerate(original_cells_data):
                current_cell_plain_text = get_plain_text_from_rich_text(cell_rich_text_list_original)
                print(f"{indent}DEBUG (Tabla):     Celda {cell_index+1} plain_text: '{current_cell_plain_text}'")
                if '$' in current_cell_plain_text and not current_cell_plain_text.strip().startswith("$$"):
                    segments = parse_text_for_inline_katex(current_cell_plain_text)
                    print(f"{indent}DEBUG (Tabla):       Resultado de parse_text_for_inline_katex para celda: {segments}")
                    if segments:
                        new_cell_rich_text_payload = []; has_meaningful_content = False
                        for seg_type, content in segments:
                            if seg_type == 'text' and content: 
                                new_cell_rich_text_payload.append({"type": "text", "text": {"content": content}})
                                if content.strip(): has_meaningful_content = True
                            elif seg_type == 'katex' and content: 
                                new_cell_rich_text_payload.append({"type": "equation", "equation": {"expression": content}})
                                has_meaningful_content = True
                        if has_meaningful_content and new_cell_rich_text_payload:
                            print(f"{indent}DEBUG (Tabla):       Celda {cell_index+1} será actualizada.")
                            new_cells_data_for_row.append(new_cell_rich_text_payload); row_was_modified = True
                        else: new_cells_data_for_row.append(cell_rich_text_list_original) 
                    else: new_cells_data_for_row.append(cell_rich_text_list_original) 
                else: new_cells_data_for_row.append(cell_rich_text_list_original) 
            if row_was_modified:
                try:
                    notion_client.blocks.update(block_id=row_id, table_row={"cells": new_cells_data_for_row})
                    print(f"{indent}DEBUG (Tabla):     Fila {row_id} actualizada exitosamente."); time.sleep(0.35)
                except Exception as e: print(f"{indent}DEBUG (Tabla):     ERROR actualizando fila {row_id}: {e}")

# ------------------------------------------------------------------------------------

def process_blocks_recursively(parent_block_id: str, notion_client: Client, depth=0):
    indent = "  " * depth
    print(f"{indent}DEBUG (Rec): Procesando hijos de parent_block_id: {parent_block_id}, Nivel: {depth}")

    current_level_blocks = []
    next_cursor = None
    try:
        while True:
            response = notion_client.blocks.children.list(block_id=parent_block_id, start_cursor=next_cursor, page_size=100)
            current_level_blocks.extend(response.get("results", []))
            next_cursor = response.get("next_cursor")
            if not next_cursor: break
    except Exception as e:
        print(f"{indent}DEBUG (Rec): Error obteniendo bloques hijos de {parent_block_id}: {e}")
        return None
            
    print(f"{indent}DEBUG (Rec): Encontrados {len(current_level_blocks)} bloques hijos para {parent_block_id}.")
    last_successfully_placed_block_id_at_this_level = None

    for i, original_block in enumerate(current_level_blocks):
        block_id = original_block["id"]
        block_type = original_block.get("type")
        has_children = original_block.get("has_children", False)

        print(f"\n{indent}DEBUG (Rec): ---- Revisando bloque {i+1}/{len(current_level_blocks)} ----")
        print(f"{indent}DEBUG (Rec):   ID: {block_id}, Tipo: {block_type}, TieneHijos: {has_children}")

        block_was_replaced_or_deleted = False

        if block_type == "table": 
            process_simple_table_rows(block_id, depth + 1, notion_client)
            last_successfully_placed_block_id_at_this_level = block_id
            continue 

        if block_type not in TEXT_BEARING_BLOCK_TYPES:
            print(f"{indent}DEBUG (Rec):   Bloque de tipo '{block_type}' no es text-bearing. Omitiendo.")
            if has_children and block_type in RECURSIVE_CHILD_BEARING_TYPES:
                 print(f"{indent}DEBUG (Rec):   Pero tiene hijos y es recursivo. Llamando para ID: {block_id}")
                 process_blocks_recursively(block_id, notion_client, depth + 1)
            last_successfully_placed_block_id_at_this_level = block_id
            continue

        rich_text_list_original = get_rich_text_list_from_block_data(original_block)
        if rich_text_list_original is None:
            print(f"{indent}DEBUG (Rec):   No se pudo extraer rich_text para '{block_type}'. Omitiendo.")
            if has_children and block_type in RECURSIVE_CHILD_BEARING_TYPES:
                 print(f"{indent}DEBUG (Rec):   Aun así, tiene hijos y es recursivo. Llamando para ID: {block_id}")
                 process_blocks_recursively(block_id, notion_client, depth + 1)
            last_successfully_placed_block_id_at_this_level = block_id
            continue
            
        plain_text = get_plain_text_from_rich_text(rich_text_list_original)
        print(f"{indent}DEBUG (Rec):   Contenido (plain_text): '{plain_text}'")

        # NUEVA LÓGICA DE PROCESAMIENTO DE BLOQUES:
        # Dividir el plain_text por ocurrencias de $$...$$
        # La regex (\$\$[\s\S]+?\$\$) captura el bloque KaTeX incluyendo los delimitadores $$
        # re.split mantendrá estos bloques KaTeX capturados en la lista resultante.
        
        # Asegurarse de que la expresión dentro de $$...$$ no sea solo espacios
        # y que los $$ no estén uno al lado del otro como $$$$ (que no es un bloque válido)
        # La regex r"(\$\$(?!\s*\$\$)[\s\S]*?\$\$)" intenta ser más específica:
        #   \$\$            -> literal $$
        #   (?!\s*\$\$)    -> negativa hacia adelante: no seguido por (cero o más espacios y luego $$) - evita $$$$
        #   [\s\S]*?       -> cualquier caracter, incluyendo saltos de línea, no codicioso
        #   \$\$            -> literal $$ de cierre
        # Esta regex es para el split.
        # La validación del contenido interno se hará después de extraerlo.

        # Regex para split: (\$\$[\s\S]+?\$\$) - captura $$equation$$
        #   [\s\S] permite saltos de línea dentro de la ecuación.
        #   +? no codicioso, para que cada ecuación se capture individualmente.
        # Si no hay $$...$$, parts tendrá un solo elemento (el plain_text original).
        parts = re.split(r"(\$\$[\s\S]+?\$\$)", plain_text)
        
        new_blocks_payloads_for_this_original_block = []
        original_block_content_changed = False

        if len(parts) > 1 or (len(parts) == 1 and parts[0].startswith("$$") and parts[0].endswith("$$") and parts[0].count("$$") == 2) : # Hay algo que procesar (o es todo un bloque $$)
            print(f"{indent}DEBUG (Rec):   Analizando partes divididas por $$...$$: {len(parts)} partes.")
            for part_index, text_segment in enumerate(parts):
                if not text_segment.strip(): # Ignorar segmentos que son solo espacios/saltos de línea vacíos
                    continue

                # Es un bloque KaTeX $$...$$
                if text_segment.startswith("$$") and text_segment.endswith("$$") and text_segment.count("$$") == 2:
                    expression = text_segment[2:-2].strip()
                    if expression:
                        print(f"{indent}DEBUG (Rec):     Parte {part_index+1} es BLOQUE KaTeX: '{expression}'")
                        new_blocks_payloads_for_this_original_block.append(create_equation_block_payload(expression))
                        original_block_content_changed = True
                    else:
                        print(f"{indent}DEBUG (Rec):     Parte {part_index+1} es BLOQUE KaTeX VACÍO ($$$$). Se tratará como texto.")
                        # Si es un $$ $$ vacío, lo tratamos como texto para que no se pierda si hay más
                        # o lo procesamos como inline si tiene $ adentro (poco probable aquí).
                        # Por ahora, si era un bloque $$ $$ vacío, se añade como texto.
                        # Si el usuario quiere que párrafos vacíos o '$$$$' se eliminen, es otra lógica.
                        # Intentar procesar el texto original '$$ $$' como inline
                        inline_segments_for_empty_block = parse_text_for_inline_katex(text_segment)
                        if inline_segments_for_empty_block:
                            rt_list = []
                            for st, sc in inline_segments_for_empty_block:
                                if st == 'text' and sc: rt_list.append({"type": "text", "text": {"content": sc}})
                                elif st == 'katex' and sc: rt_list.append({"type": "equation", "equation": {"expression": sc}})
                            if rt_list: 
                                payload = create_paragraph_block_payload_from_rich_text_list(rt_list)
                                if payload: new_blocks_payloads_for_this_original_block.append(payload)
                                original_block_content_changed = True # Marcamos cambio aunque sea sutil
                        elif text_segment.strip(): # Si no hay inline pero hay algo
                            payload = create_paragraph_block_payload_from_plain_text(text_segment)
                            if payload: new_blocks_payloads_for_this_original_block.append(payload)
                            original_block_content_changed = True


                # Es un segmento de texto (antes, entre, o después de bloques $$...$$)
                else: 
                    print(f"{indent}DEBUG (Rec):     Parte {part_index+1} es TEXTO: '{text_segment[:100]}...' (puede tener $inline$)")
                    inline_segments = parse_text_for_inline_katex(text_segment)
                    if inline_segments:
                        rich_text_list_for_paragraph = []
                        for seg_type, content in inline_segments:
                            if seg_type == 'text' and content:
                                rich_text_list_for_paragraph.append({"type": "text", "text": {"content": content}})
                            elif seg_type == 'katex' and content:
                                rich_text_list_for_paragraph.append({"type": "equation", "equation": {"expression": content}})
                        
                        if rich_text_list_for_paragraph: # Solo añadir si hay contenido real
                            payload = create_paragraph_block_payload_from_rich_text_list(rich_text_list_for_paragraph)
                            if payload: new_blocks_payloads_for_this_original_block.append(payload)
                            original_block_content_changed = True
                    elif text_segment.strip(): # Si no hay inline, pero el texto tiene contenido
                        payload = create_paragraph_block_payload_from_plain_text(text_segment)
                        if payload: new_blocks_payloads_for_this_original_block.append(payload)
                        original_block_content_changed = True # El simple hecho de separar ya es un cambio
            
            # Si el contenido original cambió (se dividió en partes o se procesó inline),
            # reemplazar el bloque original con los nuevos bloques generados.
            if original_block_content_changed and new_blocks_payloads_for_this_original_block:
                print(f"{indent}DEBUG (Rec):   --> Reemplazando bloque {block_id} con {len(new_blocks_payloads_for_this_original_block)} nuevos bloques.")
                try:
                    temp_last_id_for_insertion = last_successfully_placed_block_id_at_this_level
                    created_block_ids_for_this_op = []
                    for payload_idx, payload_data in enumerate(new_blocks_payloads_for_this_original_block):
                        response = notion_client.blocks.children.append(
                            block_id=parent_block_id, children=[payload_data],
                            after=temp_last_id_for_insertion if temp_last_id_for_insertion else None)
                        new_b_id = response['results'][0]['id']
                        print(f"{indent}DEBUG (Rec):     Nuevo bloque (parte {payload_idx+1}) creado (ID: {new_b_id}).")
                        created_block_ids_for_this_op.append(new_b_id)
                        temp_last_id_for_insertion = new_b_id
                        time.sleep(0.35)
                    
                    notion_client.blocks.delete(block_id=block_id)
                    print(f"{indent}DEBUG (Rec):     Bloque original {block_id} eliminado.")
                    if created_block_ids_for_this_op:
                        last_successfully_placed_block_id_at_this_level = created_block_ids_for_this_op[-1]
                    block_was_replaced_or_deleted = True
                    time.sleep(0.35)
                except Exception as e:
                    print(f"{indent}DEBUG (Rec):     ERROR reemplazando bloque {block_id} con nuevos segmentos: {e}")
                    last_successfully_placed_block_id_at_this_level = block_id # Falló, el original sigue
            else:
                print(f"{indent}DEBUG (Rec):   No se detectaron cambios significativos o KaTeX procesable. Bloque se mantiene.")
                last_successfully_placed_block_id_at_this_level = block_id
        else: # El bloque no contenía $$...$$, podría ser solo inline o nada.
            print(f"{indent}DEBUG (Rec):   No se encontraron bloques $$...$$ en el plain_text. Verificando solo inline $...$.")
            # Esta es la lógica original para $inline$ cuando no hay $$...$$
            if '$' in plain_text: # Ya sabemos que no es un "is_block_katex"
                segments = parse_text_for_inline_katex(plain_text)
                print(f"{indent}DEBUG (Rec):     Resultado de parse_text_for_inline_katex (solo inline): {segments}")
                if segments:
                    new_rich_text_payload_list = []
                    has_meaningful_update = False
                    for seg_type, content in segments:
                        if seg_type == 'text':
                            if content: new_rich_text_payload_list.append({"type": "text", "text": {"content": content}}); 
                            if content.strip(): has_meaningful_update = True
                        elif seg_type == 'katex':
                            if content: new_rich_text_payload_list.append({"type": "equation", "equation": {"expression": content}}); has_meaningful_update = True
                    
                    if has_meaningful_update and new_rich_text_payload_list:
                        print(f"{indent}DEBUG (Rec):   --> PROCESANDO solo como KaTeX inline. Nuevo rich_text: {new_rich_text_payload_list}")
                        update_data = {block_type: {"rich_text": new_rich_text_payload_list}}
                        type_specific_content_original = original_block.get(block_type, {})
                        if block_type == "to_do" and "checked" in type_specific_content_original:
                            update_data[block_type]["checked"] = type_specific_content_original["checked"]
                        try:
                            notion_client.blocks.update(block_id=block_id, **update_data)
                            print(f"{indent}DEBUG (Rec):     Bloque {block_id} actualizado con KaTeX inline (sin $$).")
                            time.sleep(0.35)
                        except Exception as e:
                            print(f"{indent}DEBUG (Rec):     ERROR actualizando bloque {block_id} para KaTeX inline (sin $$): {e}")
                    else: print(f"{indent}DEBUG (Rec):     No se generó payload de rich_text para actualizar (solo inline).")
                else: print(f"{indent}DEBUG (Rec):     No se encontraron segmentos KaTeX inline válidos (solo inline).")
            else:
                 print(f"{indent}DEBUG (Rec):   No contiene '$' para procesamiento inline.")
            last_successfully_placed_block_id_at_this_level = block_id

        # Recursión para bloques hijos si el bloque original NO fue reemplazado
        if not block_was_replaced_or_deleted and has_children and block_type in RECURSIVE_CHILD_BEARING_TYPES:
            print(f"{indent}DEBUG (Rec):   Bloque '{block_type}' ID {block_id} tiene hijos. Llamando recursivamente.")
            process_blocks_recursively(block_id, notion_client, depth + 1)
            
    return last_successfully_placed_block_id_at_this_level

# --- Bloque Principal de Ejecución ---
if __name__ == "__main__":
    if NOTION_API_KEY == "tu_integration_secret_aqui" or \
       PAGE_ID_TO_PROCESS == "el_id_de_tu_pagina_de_notion_aqui":
        print("ERROR SCRIPT: Por favor, establece tus variables NOTION_API_KEY y PAGE_ID_TO_PROCESS.")
    else:
        print("ADVERTENCIA: Este script realizará cambios en tu página de Notion.")
        confirm = input("¿Estás seguro de que quieres continuar y procesar la página (s/n)?: ")
        if confirm.lower() == 's':
            try:
                client = Client(auth=NOTION_API_KEY)
                process_blocks_recursively(PAGE_ID_TO_PROCESS, client, depth=0)
                print("\nProcesamiento COMPLETADO.")
            except Exception as e:
                print(f"ERROR FATAL durante la inicialización o ejecución: {e}")
        else:
            print("Procesamiento cancelado.")