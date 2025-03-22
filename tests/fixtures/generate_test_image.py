"""
テスト用の画像を生成するスクリプト
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_test_image(output_path: Path, text: str = "Test Image") -> None:
    """
    テスト用の画像を生成
    
    Args:
        output_path: 出力先のパス
        text: 画像に描画するテキスト
    """
    # 画像サイズ
    width = 400
    height = 300
    
    # 画像を作成
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    
    # テキストを描画
    text_color = "black"
    text_position = (width // 4, height // 2)
    draw.text(text_position, text, fill=text_color)
    
    # 画像を保存
    image.save(output_path)

def main():
    """メイン処理"""
    # 出力ディレクトリ
    output_dir = Path(__file__).parent / "images"
    output_dir.mkdir(exist_ok=True)
    
    # テスト用画像を生成
    generate_test_image(output_dir / "test1.jpg", "Test Image 1")
    generate_test_image(output_dir / "test2.jpg", "Test Image 2")

if __name__ == "__main__":
    main() 