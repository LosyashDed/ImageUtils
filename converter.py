import argparse
import os
import shutil
import sys
from pathlib import Path
from PIL import Image


def clear_output_directory(output_dir):
    if os.path.exists(output_dir):
        if os.listdir(output_dir):  
            print(f"Очищаю выходную папку: {output_dir}")
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
        else:
            print(f"Выходная папка уже пуста: {output_dir}")
    else:
        print(f"Создаю выходную папку: {output_dir}")
        os.makedirs(output_dir)


def get_output_filename(input_filename, target_format=None, suffix=""):
    name_without_ext = os.path.splitext(input_filename)[0]
    
    if target_format is None:
        original_ext = os.path.splitext(input_filename)[1]
        if suffix:
            return f"{name_without_ext}_{suffix}{original_ext}"
        else:
            return f"{name_without_ext}_processed{original_ext}"
    
    if suffix:
        return f"{name_without_ext}_{suffix}.{target_format.lower()}"
    return f"{name_without_ext}.{target_format.lower()}"


def resize_image(image, width=None, height=None, keep_aspect=True):
    # keep_aspect = True - сохранять пропорции, False - не сохранять

    if not width and not height:
        return image
    
    original_width, original_height = image.size
    
    if keep_aspect:
        aspect_ratio = original_width / original_height
        if width and height:
            
            if width / height > aspect_ratio:
                # Ограничиваем по высоте
                new_height = height
                new_width = int(height * aspect_ratio)
            else:
                # Ограничиваем по ширине
                new_width = width
                new_height = int(width / aspect_ratio)
        elif width:
            # Только ширина
            new_width = width
            new_height = int(width / aspect_ratio)
        else:
            # Только высота
            new_height = height
            new_width = int(height * aspect_ratio)
    else:
        new_width = width or original_width
        new_height = height or original_height
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def flip_image(image, horizontal=False, vertical=False):
    if horizontal:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if vertical:
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return image


def process_image(input_path, output_path, target_format=None, original_format=None, 
                  resize_width=None, resize_height=None, keep_aspect=True, 
                  flip_horizontal=False, flip_vertical=False):
    """
    Обработка одного изображения. Возврщает True или False.
    
    Args:
        input_path: Путь к старому файлу
        output_path: Путь к новому файлу
        target_format: Целевой формат (None чтобы оставить ихсодный)
        original_format: Оригинальный формат изображения
        resize_width: Новая ширина
        resize_height: Новая высота
        keep_aspect: Сохранять пропорции
        flip_horizontal: Горизонтальное отзеркаливание
        flip_vertical: Вертикальное отзеркаливание
    """
    try:
        with Image.open(input_path) as image:
            original_size = image.size
            
            if resize_width or resize_height:
                image = resize_image(image, resize_width, resize_height, keep_aspect)
                print(f"   Размер изменен: {original_size} → {image.size}")
            
            if flip_horizontal or flip_vertical:
                image = flip_image(image, flip_horizontal, flip_vertical)
                flip_info = []
                if flip_horizontal:
                    flip_info.append("горизонтально")
                if flip_vertical:
                    flip_info.append("вертикально")
                print(f"   Отзеркалено: {' и '.join(flip_info)}")
            
            if target_format:
                save_format = target_format.upper()
            else:
                save_format = original_format.upper() if original_format else 'JPEG'
            
            if save_format in ['JPG', 'JPEG']:
                save_format = 'JPEG'
            elif save_format in ['TIF', 'TIFF']:
                save_format = 'TIFF'
            
            formats_without_alpha = ['JPEG', 'BMP']
            
            if save_format in formats_without_alpha:
                if image.mode in ['RGBA', 'LA', 'P']:
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    rgb_image.paste(image, mask=image.getchannel('A'))
                    image = rgb_image
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
            elif save_format in ['PNG', 'WEBP', 'TIFF']:
                if image.mode in ['L', 'P']:
                    image = image.convert('RGBA')
            else:
                if image.mode in ['RGBA', 'LA', 'P']:
                    image = image.convert('RGB')

            image.save(output_path, format=save_format)
            return True
            
    except Exception as e:
        print(f"Ошибка при обработке {input_path}: {e}")
        return False


def get_supported_image_files(input_dir):
    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.tiff', '.tif'}
    image_files = []
    
    if not os.path.exists(input_dir):
        return image_files
    
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename.lower())
            if ext in supported_extensions:
                format_map = {
                    '.jpg': 'JPEG',
                    '.jpeg': 'JPEG', 
                    '.png': 'PNG',
                    '.webp': 'WEBP',
                    '.gif': 'GIF',
                    '.tiff': 'TIFF',
                    '.tif': 'TIFF'
                }
                original_format = format_map.get(ext, 'JPEG')
                
                image_files.append((file_path, original_format))
    
    return image_files


def generate_output_suffix(resize_width, resize_height, flip_horizontal, flip_vertical):
    suffix_parts = []
    
    if resize_width or resize_height:
        if resize_width and resize_height:
            suffix_parts.append(f"{resize_width}x{resize_height}")
        elif resize_width:
            suffix_parts.append(f"w{resize_width}")
        else:
            suffix_parts.append(f"h{resize_height}")
    
    if flip_horizontal and flip_vertical:
        suffix_parts.append("flip_hv")
    elif flip_horizontal:
        suffix_parts.append("flip_h")
    elif flip_vertical:
        suffix_parts.append("flip_v")
    
    return "_".join(suffix_parts)


def main():
    epilog = '''
    Примеры использования:
      # Простая конвертация формата
      python converter.py -t png
      
      # Изменение размера
      python converter.py --width 800 --height 600
      
      # Отзеркаливание
      python converter.py --flip-horizontal --flip-vertical
      
      # Конвертация с изменением размера
      python converter.py -t jpg --width 800 --height 600
      
      # Конвертация с сохранением пропорций
      python converter.py -t webp --width 1920 --keep-aspect
      
      # Комбинированные операции
      python converter.py --width 800 --flip-horizontal --input-dir ./photos --output-dir ./processed
      
      # Изменение размера без сохранения пропорций и смены формата
      python converter.py --width 800 --height 600 --no-keep-aspect
    '''

    parser = argparse.ArgumentParser(
        description='Расширенный конвертер изображений с возможностью изменения размера и отзеркаливания',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog
    )
    
    parser.add_argument(
        '-t', '--target-format',
        help='Целевой формат для конвертации (png, jpg, jpeg, webp, gif, tiff). Если не указан, формат остается прежним'
    )
    
    parser.add_argument(
        '--input-dir',
        default='./input_images',
        help='Путь к папке с исходными изображениями (по умолчанию: ./input_images)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./output_images',
        help='Путь к папке для обработанных изображений (по умолчанию: ./output_images)'
    )
    
    parser.add_argument(
        '--width',
        type=int,
        help='Новая ширина изображения в пикселях'
    )
    
    parser.add_argument(
        '--height',
        type=int,
        help='Новая высота изображения в пикселях'
    )
    
    parser.add_argument(
        '--keep-aspect',
        action='store_true',
        default=True,
        help='Сохранять пропорции при изменении размера (по умолчанию: включено)'
    )
    
    parser.add_argument(
        '--no-keep-aspect',
        action='store_true',
        help='НЕ сохранять пропорции при изменении размера'
    )
    
    parser.add_argument(
        '--flip-horizontal',
        action='store_true',
        help='Отзеркалить изображения по горизонтали'
    )
    
    parser.add_argument(
        '--flip-vertical',
        action='store_true',
        help='Отзеркалить изображения по вертикали'
    )
    
    args = parser.parse_args()
    
    # Проверка, что выбрали хотя бы одну операцию
    has_resize = args.width or args.height
    has_flip = args.flip_horizontal or args.flip_vertical
    has_format_change = args.target_format
    
    if not (has_resize or has_flip or has_format_change):
        print("❌ Ошибка: Необходимо указать хотя бы одну операцию:")
        print("   - Конвертация формата: -t <формат>")
        print("   - Изменение размера: --width и/или --height")
        print("   - Отзеркаливание: --flip-horizontal и/или --flip-vertical")
        print("\nИспользуйте --help для просмотра всех опций")
        sys.exit(1)
    
    # Другие различные проверки
    if args.target_format:
        supported_formats = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'tiff']
        if args.target_format.lower() not in supported_formats:
            print(f"❌ Ошибка: Неподдерживаемый формат - {args.target_format}")
            print(f"Поддерживаемые форматы: {', '.join(supported_formats)}")
            sys.exit(1)
    
    keep_aspect = args.keep_aspect and not args.no_keep_aspect
    
    if args.width and args.width <= 0:
        print("❌ Ошибка: Ширина должна быть положительным числом")
        sys.exit(1)
    
    if args.height and args.height <= 0:
        print("❌ Ошибка: Высота должна быть положительным числом")
        sys.exit(1)
    
    input_dir = args.input_dir
    output_dir = args.output_dir
    target_format = args.target_format.lower() if args.target_format else None
    
    print(f"🔄 Начинаю пакетную обработку изображений")
    print(f"📁 Входная папка: {input_dir}")
    print(f"📁 Выходная папка: {output_dir}")
    
    if target_format:
        print(f"🎯 Целевой формат: {target_format.upper()}")
    else:
        print(f"🎯 Формат: сохранить оригинальный")
    
    # Показываем параметры обработки
    operations = []
    if args.width or args.height:
        size_info = []
        if args.width:
            size_info.append(f"ширина: {args.width}px")
        if args.height:
            size_info.append(f"высота: {args.height}px")
        operations.append(f"📏 Изменение размера: {', '.join(size_info)} (пропорции: {'сохранять' if keep_aspect else 'не сохранять'})")
    
    if args.flip_horizontal or args.flip_vertical:
        flip_info = []
        if args.flip_horizontal:
            flip_info.append("горизонтально")
        if args.flip_vertical:
            flip_info.append("вертикально")
        operations.append(f"🔄 Отзеркаливание: {' и '.join(flip_info)}")
    
    if operations:
        print("🛠️  Дополнительные операции:")
        for operation in operations:
            print(f"   {operation}")
    
    print("-" * 60)
    
    if not os.path.exists(input_dir):
        print(f"❌ Ошибка: Входная папка {input_dir} не существует!")
        print("Создайте папку и поместите в неё изображения для обработки.")
        sys.exit(1)
    
    image_files_with_formats = get_supported_image_files(input_dir)
    
    if not image_files_with_formats:
        print(f"❌ В папке {input_dir} не найдено поддерживаемых изображений!")
        print("Поддерживаемые форматы: JPEG, PNG, WEBP, GIF, TIFF")
        sys.exit(1)
    
    print(f"📋 Найдено {len(image_files_with_formats)} изображений для обработки")
    
    clear_output_directory(output_dir)
    
    suffix = generate_output_suffix(args.width, args.height, args.flip_horizontal, args.flip_vertical)

    # Обработка изображений    
    successful_conversions = 0
    failed_conversions = 0
    
    for input_path, original_format in image_files_with_formats:
        filename = os.path.basename(input_path)
        output_filename = get_output_filename(filename, target_format, suffix)
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"🔧 Обрабатываю файл: {filename}...")
        
        if process_image(input_path, output_path, target_format, original_format,
                        args.width, args.height, keep_aspect,
                        args.flip_horizontal, args.flip_vertical):
            print(f"✅ Файл {filename} обработан → {output_filename}")
            successful_conversions += 1
        else:
            print(f"❌ Не удалось обработать файл: {filename}")
            failed_conversions += 1
    
    print("-" * 60)
    print("🎉 Обработка завершена!")
    print(f"✅ Успешно обработано: {successful_conversions} файлов")
    print(f"❌ Ошибок обработки: {failed_conversions} файлов")
    print(f"📁 Обработанные файлы находятся в папке: {output_dir}")


if __name__ == '__main__':
    main() 