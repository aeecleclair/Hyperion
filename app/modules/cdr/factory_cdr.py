import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.cruds_groups import get_groups
from app.core.groups.factory_groups import CoreGroupsFactory
from app.core.memberships import cruds_memberships
from app.core.memberships.factory_memberships import CoreMembershipsFactory
from app.core.permissions import cruds_permissions, schemas_permissions
from app.core.users.factory_users import CoreUsersFactory
from app.core.utils.config import Settings
from app.modules.cdr import coredata_cdr, cruds_cdr, models_cdr
from app.types.factory import Factory


class CdrFactory(Factory):
    depends_on = [CoreUsersFactory, CoreGroupsFactory, CoreMembershipsFactory]

    @classmethod
    async def run(cls, db: AsyncSession, settings: Settings) -> None:
        n = 0
        groups = await get_groups(db=db)
        if groups:
            for group in groups:
                n += 1
                seller = models_cdr.Seller(
                    id=uuid.uuid4(),
                    name=group.name,
                    group_id=group.id,
                    order=n,
                )
                cruds_cdr.create_seller(db=db, seller=seller)

        sellers = await cruds_cdr.get_sellers(db=db)

        curriculum = models_cdr.Curriculum(
            id=uuid.uuid4(),
            name="généraliste",
        )
        cruds_cdr.create_curriculum(db=db, curriculum=curriculum)

        eclair = next((seller for seller in sellers if seller.name == "ECLAIR"), None)
        bazar = next((seller for seller in sellers if seller.name == "Bazar"), None)
        AEECL = next((seller for seller in sellers if seller.name == "AEECL"), None)
        USEECL = next((seller for seller in sellers if seller.name == "USEECL"), None)
        interest1 = models_cdr.CdrProduct(
            id=uuid.uuid4(),
            seller_id=eclair.id,
            name_fr="Interêt pour l'asso",
            name_en="Interest for the club",
            available_online=False,
            needs_validation=False,
            product_constraints=[],
            document_constraints=[],
            year=coredata_cdr.CdrYear().year,
        )
        interest1_variant = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=interest1.id,
            name_fr="Prétendances",
            name_en="English pretendances idk",
            price=0,
            enabled=True,
            unique=True,
            year=coredata_cdr.CdrYear().year,
        )
        interest2 = models_cdr.CdrProduct(
            id=uuid.uuid4(),
            seller_id=bazar.id,
            name_fr="Interêt pour l'asso",
            name_en="Interest for the club",
            available_online=False,
            needs_validation=False,
            product_constraints=[],
            document_constraints=[],
            year=coredata_cdr.CdrYear().year,
        )
        interest2_variant = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=interest2.id,
            name_fr="Prétendances",
            name_en="English pretendances idk",
            price=0,
            enabled=True,
            unique=True,
            year=coredata_cdr.CdrYear().year,
        )
        cruds_cdr.create_product(db=db, product=interest1)
        cruds_cdr.create_product(db=db, product=interest2)
        cruds_cdr.create_product_variant(db=db, product_variant=interest1_variant)
        cruds_cdr.create_product_variant(db=db, product_variant=interest2_variant)

        memberships = await cruds_memberships.get_association_memberships(db=db)
        membership_aeecl = next(
            (membership for membership in memberships if membership.name == "AEECL"),
            None,
        )
        membership_useecl = next(
            (membership for membership in memberships if membership.name == "USEECL"),
            None,
        )

        membership_aeecl_product = models_cdr.CdrProduct(
            id=uuid.uuid4(),
            seller_id=AEECL.id,
            name_fr="Adhésion AEECL",
            name_en="AEECL Membership",
            available_online=True,
            needs_validation=True,
            related_membership_id=membership_aeecl.id,
            product_constraints=[],
            document_constraints=[],
            year=coredata_cdr.CdrYear().year,
        )
        membership_aeecl_variant_1 = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=membership_aeecl_product.id,
            name_fr="1 an",
            name_en="1 year",
            price=4000,
            enabled=True,
            unique=True,
            year=coredata_cdr.CdrYear().year,
            related_membership_added_duration=timedelta(days=365),
        )
        membership_aeecl_variant_2 = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=membership_aeecl_product.id,
            name_fr="3 ans",
            name_en="3 years",
            price=10000,
            enabled=True,
            unique=True,
            year=coredata_cdr.CdrYear().year,
            related_membership_added_duration=timedelta(days=365),
        )
        membership_useecl_product = models_cdr.CdrProduct(
            id=uuid.uuid4(),
            seller_id=USEECL.id,
            name_fr="Adhésion USEECL",
            name_en="USEECL Membership",
            available_online=True,
            needs_validation=True,
            related_membership_id=membership_useecl.id,
            product_constraints=[],
            document_constraints=[],
            year=coredata_cdr.CdrYear().year,
        )
        membership_useecl_variant_1 = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=membership_useecl_product.id,
            name_fr="1 an",
            name_en="1 year",
            price=4000,
            enabled=True,
            unique=True,
            year=coredata_cdr.CdrYear().year,
            related_membership_added_duration=timedelta(days=365),
        )
        membership_useecl_variant_2 = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=membership_useecl_product.id,
            name_fr="3 ans",
            name_en="3 years",
            price=10000,
            enabled=True,
            unique=True,
            year=coredata_cdr.CdrYear().year,
            related_membership_added_duration=timedelta(days=365),
        )
        cruds_cdr.create_product(db=db, product=membership_aeecl_product)
        cruds_cdr.create_product(db=db, product=membership_useecl_product)
        cruds_cdr.create_product_variant(
            db=db, product_variant=membership_aeecl_variant_1
        )
        cruds_cdr.create_product_variant(
            db=db, product_variant=membership_aeecl_variant_2
        )
        cruds_cdr.create_product_variant(
            db=db, product_variant=membership_useecl_variant_1
        )
        cruds_cdr.create_product_variant(
            db=db, product_variant=membership_useecl_variant_2
        )

        sacoche = models_cdr.CdrProduct(
            id=uuid.uuid4(),
            seller_id=AEECL.id,
            name_fr="Sacoche banane moche",
            name_en="Ugly bag",
            available_online=False,
            needs_validation=True,
            product_constraints=[membership_aeecl_product],
            document_constraints=[],
            year=coredata_cdr.CdrYear().year,
        )
        sacoche_variant = models_cdr.ProductVariant(
            id=uuid.uuid4(),
            product_id=sacoche.id,
            name_fr="sacoche",
            name_en="bag",
            price=1500,
            enabled=True,
            unique=False,
            year=coredata_cdr.CdrYear().year,
        )
        cruds_cdr.create_product(db=db, product=sacoche)
        cruds_cdr.create_product_variant(db=db, product_variant=sacoche_variant)

    @classmethod
    async def should_run(cls, db: AsyncSession):
        campaigns = await cruds_cdr.get_curriculums(db=db)
        return len(campaigns) == 0
