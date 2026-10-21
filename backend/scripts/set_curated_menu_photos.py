"""Attach one verified online food photo to every current Spice Hub dish.

The URLs below were individually searched by dish name.  They are deliberately
stored on the menu item (rather than guessed in either frontend) so the admin
and customer sites always render the identical, dish-specific picture.
"""

# ruff: noqa: E402, E501

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.menu import MenuItem


PHOTO_URLS: dict[str, str] = {
    "BF-IDL": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto/FOOD_CATALOG/IMAGES/CMS/2025/2/16/dde749d2-67b2-42b8-a877-3fc05071dba3_2a5a1119-588e-451b-a939-07c438a97741.jpg",
    "BF-PD": "https://static.wixstatic.com/media/ec36cd_7971b6e4ea464d6f8797f9a1e80b2905~mv2.jpg",
    "BF-MD": "https://img-cdn.publive.online/fit-in/1200x675/indian-express-malayalam/media/media_files/2025/11/20/masala-dosa-fi-2025-11-20-13-57-40.jpg",
    "BF-SD": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2025/5/26/2327f3e8-c761-4a18-b26c-b97bba87e3c6_15f762d3-2629-4dd4-99ff-e72860cd1443.jpg",
    "BF-PB": "https://image.cdn.shpy.in/360704/pooriwithsabji-1737971345316.jpeg?format=webp",
    "LM-VM": "https://dt4l9bx31tioh.cloudfront.net/eazymedia/group/6744/menu020250324141151.jpg?height=450&mode=fit%3Fformat%3Dauto&quality=80&width=818",
    "LM-SVM": "https://images.deliveryhero.io/image/talabat/MenuItems/Special_Veg_Thali638975379315405242.jpg",
    "LM-SIM": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2026/2/27/f538b873-7d15-4832-866c-8d8056f444ea_c9ad668a-ffd1-460b-a8b7-e5db1a0cb208.jpg",
    "LM-CM": "https://static.punjabkesari.in/multimedia/2022_12image_13_32_135085233meerutnonvej.jpg",
    "LM-FM": "https://media-assets.swiggy.com/swiggy/image/upload/f_auto%2Cq_auto%2Cfl_lossy/RX_THUMBNAIL/IMAGES/VENDOR/2026/1/7/96d789ae-09cf-47de-b419-5f2001f1a607_1299954.jpg",
    "LR-SR": "https://parade.com/.image/MjA5MzMwNzkyNjQyMzg5MTk4/cooked-white-rice.jpg?ar=4-3&io=1&profile=w2560",
    "LR-JR": "https://static.toiimg.com/thumb/53542259.cms?height=900&width=1200",
    "LR-GR": "https://cdn.tarladalal.com/media/Ghee%20Rice.webp",
    "LR-VP": "https://www.zeerah.ca/cdn/shop/products/vegetablepulao.jpg?v=1595618736",
    "LR-EFR": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto/FOOD_CATALOG/IMAGES/CMS/2024/9/3/f97736e7-fa88-440d-b60d-333654de008b_ed824215-59d8-49fb-8733-16c42acebca9.jpg",
    "BY-VB": "https://b.zmtcdn.com/data/dish_photos/05c/3b226b4099bbb35529000fec6e27305c.jpeg",
    "BY-EB": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/5e5b691930beefd542889cabb261aaf0",
    "CB": "https://images.squarespace-cdn.com/content/v1/68c77cf65249353d1a5d9806/0ba9c337-41bf-4cfd-bb69-6c400d557b61/Chicken-Biryani-Recipe.jpg",
    "BY-CDB": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_400/RX_THUMBNAIL/IMAGES/VENDOR/2026/2/13/1b232644-0c62-46d6-8d74-d2e1431ee9b3_1327232.jpg",
    "BY-MB": "https://shopofiles.applifiles.com/public/uploads/media/vRshl4zIGZSENHcbpturgzRjNuKjllVsYZFDsL0l.jpg",
    "BR-KP": "https://i0.wp.com/gomathirecipes.com/wp-content/uploads/2021/09/parotta.jpg?fit=1077%2C720&ssl=1",
    "BR-CH": "https://image.cdn.shpy.in/362528/steptodowncom9707892-1757240709114.jpeg?format=webp",
    "BR-TR": "https://thaliflavoursofindia.co.uk/uploads/1764763104_2015a16d220e07e97f63.png",
    "BR-PN": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/e163d45445bb78997a42534af41ae297",
    "BR-BN": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2025/12/10/f4a8a2cb-959c-47c5-a6b0-d2e82f249efd_d8b3f273-049d-4d03-8c10-52eb127063cf.jpg",
    "VC-PBM": "https://dcmasala.in/assets/images/paneer_butter.jpg",
    "VC-KP": "https://image.cdn.shpy.in/301880/1694016843576_BestKadaiPaneerRecipe.jpeg?format=webp",
    "VC-DF": "https://2.bp.blogspot.com/-VEUvXVMsU2U/Uda1aaABGDI/AAAAAAAACFg/ZMOzK_U5VGc/s1600/best%2C%2Bsimple%2Band%2Bdelicious%2Bdal%2Bfry%2Bor%2Btadka.jpg",
    "VC-VK": "https://images.slurrp.com/prod/recipe_images/transcribe/main%20course/Veg-Kurma.webp",
    "VC-CM": "https://www.biryanibowl.indiafoodnj.com/files/menu/chana-masala.jpg",
    "NC-CC": "https://images.malayalamtv9.com/uploads/2026/02/Curry-1.jpg?w=400",
    "NC-BC": "https://rushable-public.s3.amazonaws.com/Media/40601913/99866311/75258756/22986430/22JnGsyUxcEOcYd87EsQFMvKmOogqIdY5AQKRzfM.jpg",
    "NC-CCN": "https://snapcalorie-webflow-website.s3.us-east-2.amazonaws.com/media/recipe_pics_v2/medium/chicken_chettinad.jpg",
    "NC-MC": "https://myblacktree.com/cdn/shop/files/nadan_mutton_curry-removebg-preview.png?v=1691221196",
    "NC-EC": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2024/9/10/23da3ec2-c50c-4060-919e-22b49b9078e8_4330f2de-11c4-475e-96fc-6f460da022ce.png",
    "MD-AFM": "https://media-assets.swiggy.com/swiggy/image/upload/f_auto%2Cq_auto%2Cfl_lossy/RX_THUMBNAIL/IMAGES/VENDOR/2025/11/25/10f82a67-3848-4384-9d01-bf1264507a3f_1271371.JPG",
    "MD-BQM": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2025/6/3/8d63e9f6-8965-47c5-9a5c-3aa2a68006b4_794f1de3-2ec7-4ab9-b7d0-727299d2a6ce.jpg",
    "MD-TDM": "https://b.zmtcdn.com/data/pictures/chains/9/21704789/92262d7130c656e201f56eeea7efa2bc.jpg",
    "MD-AFC": "https://i.pinimg.com/originals/7a/4d/4d/7a4d4ddc72be182d7230d1b7178f40c6.jpg",
    "MD-GC": "https://s3-ap-southeast-1.amazonaws.com/assets.limetray.com/assets/user_images/menus/original/1686031361_WhatsAppImage20230606at11.32.26AM.jpeg",
    "SV-GM": "https://dasaraindiancuisine.com/pluto-images/funnel/images/c2dcbb67-8866-45de-a0b9-0ceed5168b65?fit=cover&w=640",
    "SV-P65": "https://cdn.uengage.io/uploads/23764/image-7517-1770342454.jpg",
    "SV-CP": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2024/9/30/257a2b99-1ea5-4aea-be15-fb5208ef61e9_df70c03d-02ed-43e6-86e7-eef3d3035b81.jpg",
    "SV-FF": "https://foodphilosophy.uk/images/f3.png",
    "SV-VM": "https://cdn.tarladalal.com/media/veg_momos_I6QyZnD.webp",
    "SC-C65": "https://onestophalal.com/cdn/shop/articles/chicken_65_recipe_800x.jpg?v=1728185058",
    "SC-CC": "https://pupswithchopsticks.com/wp-content/uploads/chilli-chicken-thumbnail.jpg",
    "SC-CLL": "https://mybiriyanitpt.com/menu-items/chicken_lollipop.png",
    "SC-CKB": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2024/3/29/709445d4-0456-437e-90c7-2ac95bf45229_ab4c70d1-e115-4309-8f20-8dca7259aefd.JPG",
    "SC-CTK": "https://static.wixstatic.com/media/6e28fb_57ea7b17375e47aa853a0253b3ccb01a~mv2.png/v1/fill/w_980%2Ch_815%2Cal_c%2Cq_90%2Cusm_0.66_1.00_0.01%2Cenc_avif%2Cquality_auto/6e28fb_57ea7b17375e47aa853a0253b3ccb01a~mv2.png",
    "SF-FF": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto/FOOD_CATALOG/IMAGES/CMS/2025/9/2/e53c8e24-cd89-455c-8e5e-0d2596f718f3_d258bc22-55f6-413c-b679-ace50cdcd6ee.jpg_compressed",
    "SF-ATF": "https://upload.wikimedia.org/wikipedia/commons/6/6f/Anjal_Fish_Tawa_Fry_2.jpg",
    "SF-PRF": "https://images.mindtrip.ai/restaurants/dd02/ccc5/9027/4e88/f9cb/ed5e/92b6/0b28",
    "SF-FFG": "https://static.independent.co.uk/s3fs-public/thumbnails/image/2018/11/02/18/istock-170115686.jpg",
    "SF-GFP": "https://static.toiimg.com/thumb/66635052.cms?height=800&imgsize=583896&width=800",
    "RK-VRL": "https://shrisbakery.com/css/Images/chef-specials/veg-kathi.jpg",
    "RK-ERL": "https://t1.gstatic.com/images?q=tbn%3AANd9GcS498puGWtwEll3FSEV0oIN3Pvt3UtV0rGHNNOejjjLEquZBmEi",
    "RK-CRL": "https://media-assets.swiggy.com/swiggy/image/upload/f_auto%2Cq_auto%2Cfl_lossy/RX_THUMBNAIL/IMAGES/VENDOR/2025/2/13/522764f1-489c-4938-9d12-6de426121fe2_1043786.jpg",
    "RK-CSH": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto/tfvvvad6dxd3a1an43yz",
    "RK-CBG": "https://pizzabank.pk/admin-panel/laravel_code/storage/app/public/menuitems/27BQ5iLvDCW3Q4v5qKZDf1MMLMrjCLrWHPpIIoSD.png",
    "SP-TOM": "https://sc02.alicdn.com/kf/H6c74fea72cc64267aaebb4c201364cfel.png",
    "SP-CRN": "https://static.toiimg.com/photo/88198991.cms",
    "SP-VCL": "https://cdn.tiemchunglongchau.com.vn/cam_lanh_uong_gi_tot_nhat_cho_suc_khoe_cac_thuc_pham_nen_kieng_3_d933c4c242.png",
    "SP-CCL": "https://akcdn.detik.net.id/visual/2023/02/23/resep-sup-ayam-kampung-kaldu-bening_11.jpeg?q=90&w=720",
    "SP-MCW": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2024/7/21/11dbc47c-eddf-425f-b055-2fa96926b4da_3eaee856-dcef-4955-aba6-12d770629d45.jpg",
    "BJ-LIM": "https://images.rawpixel.com/image_800/cHJpdmF0ZS9sci9pbWFnZXMvd2Vic2l0ZS8yMDIzLTAxL2ZmNTkwNC1pbWFnZS1qb2IxNTI3LmpwZw.jpg",
    "BJ-ORG": "https://quecomestible.com/imagenes/zumo-de-naranja-nfc-que-es-beneficios-y-por-que-es-distinto-al-zumo-convencional-1768382302-680x580.jpg",
    "BJ-WML": "https://media.tampang.com/tm_images/article/202407/jusjpgxacblaq6er69yvafv89fpu.jpg",
    "BJ-MSB": "https://i0.wp.com/marudhuskitchen.com/wp-content/uploads/2015/08/sweet-lime-juice.jpg?resize=600%2C800",
    "BJ-MXF": "https://www.sharjahcoop.ae/medias/1200Wx1200H-00000-6291010901041-001.jpg?context=bWFzdGVyfGltYWdlc3wxMDM4NzZ8aW1hZ2UvanBlZ3xhRGcwTDJneU1DOHhNREEwTWpFek5qTTJNekF6T0M4eE1qQXdWM2d4TWpBd1NGOHdNREF3TUY4Mk1qa3hNREV3T1RBeE1EUXhYekF3TVM1cWNHY3xiYWUyNjZhMDE1NjdhMDRkMzA3N2Q4MjM0ODIyMGE5NzkzMzUzZmE0ZmYwOGI3ODM0ZDllMDliMDFjZTdmZWE1",
    "BM-CHK": "https://lessaveursdematante.com/cdn/shop/files/f7b9f6f9-1837-49e6-9333-08b92508031a.jpg?v=1752170822",
    "BM-ORO": "https://tb-static.uber.com/prod/image-proc/processed_images/d11d67155f6ca699d20489dc2587e62c/70aa2a4db7f990373ca9c376323e.jpeg",
    "BM-MNG": "https://b.zmtcdn.com/data/dish_photos/5dd/59c4f15331b9b094c1c890b685c925dd.png",
    "BM-COF": "https://media-assets.swiggy.com/swiggy/image/upload/f_auto%2Cq_auto%2Cfl_lossy/RX_THUMBNAIL/IMAGES/VENDOR/2026/3/10/056f0dff-a2a4-45a7-8897-f5b99cb89d4a_1298049.JPG",
    "BM-LSS": "https://www.sharmispassions.com/wp-content/uploads/2023/08/sweet-lassi3.jpg",
    "BD-SPR": "https://www.coca-cola.com/content/dam/onexp/mm/my/brands/sprite/myanmar_sprite_250ml_product_1100x1100%20%281%29.jpg",
    "BD-COL": "https://i5-images.massmart.co.za/asr/3105c35c-20a6-4b2d-a782-10814cd7bd8b.87babd931f56d21254c8c454296058ac.jpeg?odnBg=FFFFFF&odnHeight=636&odnWidth=694",
    "BD-THM": "https://www.indiaathome.com.au/cdn/shop/files/Thumsup_Can.png?v=1779760811",
    "BD-TEA": "https://pimwp.s3-accelerate.amazonaws.com/2020/09/tea-culture-1024x683.jpg",
    "BD-COF": "https://madrasi.in/images/demo/menu-main/menu-item-large-01.jpg",
    "DS-VAN": "https://cakexclusive.be/cdn/shop/files/ijs_2.jpg?v=1733861800&width=1946",
    "DS-CHO": "https://img.postershop.me/cdn-cgi/image/width%3D1024%2Cformat%3Dwebp/https%3A/img.postershop.me/26390/45d2ee84-1c3b-4332-84a9-675b25e146ef_image.png",
    "DS-BRW": "https://b.zmtcdn.com/data/pictures/chains/1/19111671/4efbe06e11d4855dd213c5c3bc390c2f.jpg",
    "DS-GJM": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_400/RX_THUMBNAIL/IMAGES/VENDOR/2025/12/4/c452ecca-3f91-4958-88d6-850d7da45238_207616%20%281%29.jpg",
    "DS-FAL": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto/wre6md9xkbgpaqarhlfg",
    "CH-VFR": "https://img.clevup.in/438877/SKU-0497_0-1750519506788.jpg?format=webp&width=600",
    "CH-EFR": "https://photos.tryotter.com/menu-photos/3a4541f0-dbea-49b2-ac40-125429564446.jpeg",
    "CH-CFR": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto%2Cw_300%2Ch_300%2Ce_grayscale%2Cc_fit/FOOD_CATALOG/IMAGES/CMS/2025/10/9/015b639a-c16d-4804-af0c-4dd0123d2627_888749b0-049b-4764-8e67-ce83d6b2b10d.jpg",
    "CH-CHN": "https://media-assets.swiggy.com/swiggy/image/upload/fl_lossy%2Cf_auto%2Cq_auto/FOOD_CATALOG/IMAGES/CMS/2025/2/20/ad8ad164-b5bf-47c5-b9c5-94d620f5f937_624c5296-6ff8-47c3-994c-dc8901089a82.jpg",
    "CH-CMD": "https://adm.madyafoodz.sg/Dynamic/Products/79/Images/chickenman.jpg",
}


async def run(apply: bool) -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            items = list((await session.execute(select(MenuItem).where(MenuItem.item_code.in_(PHOTO_URLS)))).scalars())
            found = {item.item_code.upper() for item in items}
            missing = sorted(set(PHOTO_URLS) - found)
            print(f"Matched {len(items)} dishes; missing {len(missing)}: {', '.join(missing) or 'none'}")
            if not apply:
                print("DRY RUN: no image URLs changed. Pass --apply to save these photos.")
                await session.rollback()
            else:
                for item in items:
                    item.image_url = PHOTO_URLS[item.item_code.upper()]
                print(f"Saved {len(items)} dish-specific online photo URLs.")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set curated online photos for the Spice Hub catalog.")
    parser.add_argument("--apply", action="store_true", help="Save the URLs (default is a dry run).")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.apply)))
