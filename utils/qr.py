import qrcode
from io import BytesIO
import base64

def make_qrcode(runner_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # higher error correction
        box_size=10,
        border=4,
    )
    qr.add_data(runner_id)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert image to base64
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    data = base64.b64encode(img_io.getvalue()).decode('ascii')

    return data
