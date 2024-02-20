"""init

Revision ID: f20685c9761e
Revises: 
Create Date: 2024-02-20 22:10:15.519878

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f20685c9761e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('advert_advertisers',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('group_manager_id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_advert_advertisers_id'), 'advert_advertisers', ['id'], unique=False)
    op.create_table('amap_delivery',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('delivery_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_amap_delivery_delivery_date'), 'amap_delivery', ['delivery_date'], unique=False)
    op.create_index(op.f('ix_amap_delivery_id'), 'amap_delivery', ['id'], unique=False)
    op.create_table('amap_information',
    sa.Column('unique_id', sa.String(), nullable=False),
    sa.Column('manager', sa.String(), nullable=False),
    sa.Column('link', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('unique_id')
    )
    op.create_index(op.f('ix_amap_information_unique_id'), 'amap_information', ['unique_id'], unique=False)
    op.create_table('amap_product',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_amap_product_category'), 'amap_product', ['category'], unique=False)
    op.create_index(op.f('ix_amap_product_id'), 'amap_product', ['id'], unique=False)
    op.create_index(op.f('ix_amap_product_name'), 'amap_product', ['name'], unique=True)
    op.create_table('authorization_code',
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('expire_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('scope', sa.String(), nullable=True),
    sa.Column('redirect_uri', sa.String(), nullable=True),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('nonce', sa.String(), nullable=True),
    sa.Column('code_challenge', sa.String(), nullable=True),
    sa.Column('code_challenge_method', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('code')
    )
    op.create_index(op.f('ix_authorization_code_code'), 'authorization_code', ['code'], unique=False)
    op.create_table('campaign_sections',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('campaign_status',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('waiting', 'open', 'closed', 'counting', 'published', name='statustype'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('campaign_voter_groups',
    sa.Column('group_id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('group_id')
    )
    op.create_table('cinema_session',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duration', sa.Integer(), nullable=False),
    sa.Column('overview', sa.String(), nullable=True),
    sa.Column('genre', sa.String(), nullable=True),
    sa.Column('tagline', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('core_group',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_core_group_id'), 'core_group', ['id'], unique=False)
    op.create_index(op.f('ix_core_group_name'), 'core_group', ['name'], unique=True)
    op.create_table('core_user',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('firstname', sa.String(), nullable=False),
    sa.Column('nickname', sa.String(), nullable=True),
    sa.Column('birthday', sa.Date(), nullable=True),
    sa.Column('promo', sa.Integer(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('floor', sa.Enum('Autre', 'Adoma', 'Exte', 'T1', 'T2', 'T3', 'T4', 'T56', 'U1', 'U2', 'U3', 'U4', 'U56', 'V1', 'V2', 'V3', 'V45', 'V6', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', name='floorstype'), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_core_user_email'), 'core_user', ['email'], unique=True)
    op.create_index(op.f('ix_core_user_id'), 'core_user', ['id'], unique=False)
    op.create_table('core_user_recover_request',
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('reset_token', sa.String(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expire_on', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('reset_token')
    )
    op.create_table('core_user_unconfirmed',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('account_type', sa.String(), nullable=False),
    sa.Column('activation_token', sa.String(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expire_on', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('loaner',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('group_manager_id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_loaner_id'), 'loaner', ['id'], unique=False)
    op.create_table('module_visibility',
    sa.Column('root', sa.String(), nullable=False),
    sa.Column('allowed_group_id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('root', 'allowed_group_id')
    )
    op.create_table('notification_message',
    sa.Column('context', sa.String(), nullable=False),
    sa.Column('firebase_device_token', sa.String(), nullable=False),
    sa.Column('is_visible', sa.Boolean(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('content', sa.String(), nullable=True),
    sa.Column('action_module', sa.String(), nullable=True),
    sa.Column('action_table', sa.String(), nullable=True),
    sa.Column('delivery_datetime', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expire_on', sa.Date(), nullable=False),
    sa.PrimaryKeyConstraint('context', 'firebase_device_token')
    )
    op.create_index(op.f('ix_notification_message_context'), 'notification_message', ['context'], unique=False)
    op.create_index(op.f('ix_notification_message_firebase_device_token'), 'notification_message', ['firebase_device_token'], unique=False)
    op.create_table('advert_adverts',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('advertiser_id', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tags', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['advertiser_id'], ['advert_advertisers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('amap_cash',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('balance', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('amap_delivery_content',
    sa.Column('product_id', sa.String(), nullable=False),
    sa.Column('delivery_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['amap_delivery.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['amap_product.id'], ),
    sa.PrimaryKeyConstraint('product_id', 'delivery_id')
    )
    op.create_table('amap_order',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('delivery_id', sa.String(), nullable=False),
    sa.Column('order_id', sa.String(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('collection_slot', sa.Enum('midi', 'soir', name='amapslottype'), nullable=False),
    sa.Column('ordering_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('delivery_date', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['delivery_id'], ['amap_delivery.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('order_id')
    )
    op.create_index(op.f('ix_amap_order_delivery_id'), 'amap_order', ['delivery_id'], unique=False)
    op.create_index(op.f('ix_amap_order_order_id'), 'amap_order', ['order_id'], unique=False)
    op.create_table('booking_manager',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('group_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['core_group.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('calendar_events',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('organizer', sa.String(), nullable=False),
    sa.Column('applicant_id', sa.String(), nullable=False),
    sa.Column('start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('all_day', sa.Boolean(), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.Column('type', sa.Enum('eventAE', 'eventUSE', 'independentAssociation', 'happyHour', 'direction', 'nightParty', 'other', name='calendareventtype'), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('decision', sa.String(), nullable=False),
    sa.Column('recurrence_rule', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['applicant_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_events_id'), 'calendar_events', ['id'], unique=False)
    op.create_table('campaign_has_voted',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('section_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['section_id'], ['campaign_sections.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'section_id')
    )
    op.create_table('campaign_lists',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('section_id', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('program', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['section_id'], ['campaign_sections.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('core_membership',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('group_id', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['core_group.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'group_id')
    )
    op.create_table('core_user_email_migration_code',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('new_email', sa.String(), nullable=False),
    sa.Column('old_email', sa.String(), nullable=False),
    sa.Column('confirmation_token', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'confirmation_token')
    )
    op.create_table('loan',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('borrower_id', sa.String(), nullable=False),
    sa.Column('loaner_id', sa.String(), nullable=False),
    sa.Column('start', sa.Date(), nullable=False),
    sa.Column('end', sa.Date(), nullable=False),
    sa.Column('notes', sa.TEXT(), nullable=True),
    sa.Column('caution', sa.String(), nullable=True),
    sa.Column('returned', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['borrower_id'], ['core_user.id'], ),
    sa.ForeignKeyConstraint(['loaner_id'], ['loaner.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loan_borrower_id'), 'loan', ['borrower_id'], unique=False)
    op.create_index(op.f('ix_loan_id'), 'loan', ['id'], unique=False)
    op.create_index(op.f('ix_loan_loaner_id'), 'loan', ['loaner_id'], unique=False)
    op.create_table('loaner_item',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('loaner_id', sa.String(), nullable=False),
    sa.Column('suggested_caution', sa.Integer(), nullable=False),
    sa.Column('total_quantity', sa.Integer(), nullable=False),
    sa.Column('suggested_lending_duration', sa.Interval(), nullable=False),
    sa.ForeignKeyConstraint(['loaner_id'], ['loaner.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loaner_item_id'), 'loaner_item', ['id'], unique=False)
    op.create_table('notification_firebase_devices',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('firebase_device_token', sa.String(), nullable=False),
    sa.Column('register_date', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('firebase_device_token')
    )
    op.create_index(op.f('ix_notification_firebase_devices_firebase_device_token'), 'notification_firebase_devices', ['firebase_device_token'], unique=False)
    op.create_table('notification_topic_membership',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('topic', sa.Enum('cinema', 'advert', 'bookingadmin', 'amap', 'booking', 'event', 'loan', 'raffle', 'vote', name='topic'), nullable=False),
    sa.Column('topic_identifier', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'topic', 'topic_identifier')
    )
    op.create_index(op.f('ix_notification_topic_membership_topic'), 'notification_topic_membership', ['topic'], unique=False)
    op.create_table('raffle',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('status', sa.Enum('creation', 'open', 'lock', name='rafflestatustype'), nullable=False),
    sa.Column('group_id', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['core_group.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raffle_description'), 'raffle', ['description'], unique=False)
    op.create_index(op.f('ix_raffle_group_id'), 'raffle', ['group_id'], unique=False)
    op.create_index(op.f('ix_raffle_id'), 'raffle', ['id'], unique=False)
    op.create_table('raffle_cash',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('balance', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('refresh_token',
    sa.Column('client_id', sa.String(), nullable=False),
    sa.Column('created_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expire_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_on', sa.DateTime(timezone=True), nullable=True),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('scope', sa.String(), nullable=True),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('nonce', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('token')
    )
    op.create_index(op.f('ix_refresh_token_client_id'), 'refresh_token', ['client_id'], unique=False)
    op.create_index(op.f('ix_refresh_token_token'), 'refresh_token', ['token'], unique=True)
    op.create_table('amap_order_content',
    sa.Column('product_id', sa.String(), nullable=False),
    sa.Column('order_id', sa.String(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['amap_order.order_id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['amap_product.id'], ),
    sa.PrimaryKeyConstraint('product_id', 'order_id')
    )
    op.create_table('booking_room',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('manager_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['manager_id'], ['booking_manager.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('campaign_lists_membership',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('list_id', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['list_id'], ['campaign_lists.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'list_id')
    )
    op.create_table('campaign_votes',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('list_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['list_id'], ['campaign_lists.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('loan_content',
    sa.Column('loan_id', sa.String(), nullable=False),
    sa.Column('item_id', sa.String(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['loaner_item.id'], ),
    sa.ForeignKeyConstraint(['loan_id'], ['loan.id'], ),
    sa.PrimaryKeyConstraint('loan_id', 'item_id')
    )
    op.create_table('raffle_pack_ticket',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('pack_size', sa.Integer(), nullable=False),
    sa.Column('raffle_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['raffle_id'], ['raffle.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raffle_pack_ticket_id'), 'raffle_pack_ticket', ['id'], unique=False)
    op.create_index(op.f('ix_raffle_pack_ticket_raffle_id'), 'raffle_pack_ticket', ['raffle_id'], unique=False)
    op.create_table('raffle_prize',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('raffle_id', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['raffle_id'], ['raffle.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raffle_prize_id'), 'raffle_prize', ['id'], unique=False)
    op.create_index(op.f('ix_raffle_prize_raffle_id'), 'raffle_prize', ['raffle_id'], unique=False)
    op.create_table('booking',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('reason', sa.String(), nullable=False),
    sa.Column('start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('note', sa.String(), nullable=True),
    sa.Column('room_id', sa.String(), nullable=False),
    sa.Column('key', sa.Boolean(), nullable=False),
    sa.Column('decision', sa.String(), nullable=False),
    sa.Column('recurrence_rule', sa.String(), nullable=True),
    sa.Column('applicant_id', sa.String(), nullable=False),
    sa.Column('entity', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['applicant_id'], ['core_user.id'], ),
    sa.ForeignKeyConstraint(['room_id'], ['booking_room.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_booking_id'), 'booking', ['id'], unique=False)
    op.create_index(op.f('ix_booking_room_id'), 'booking', ['room_id'], unique=False)
    op.create_table('raffle_ticket',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('pack_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('winning_prize', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['pack_id'], ['raffle_pack_ticket.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ),
    sa.ForeignKeyConstraint(['winning_prize'], ['raffle_prize.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_raffle_ticket_id'), 'raffle_ticket', ['id'], unique=False)
    op.create_index(op.f('ix_raffle_ticket_winning_prize'), 'raffle_ticket', ['winning_prize'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_raffle_ticket_winning_prize'), table_name='raffle_ticket')
    op.drop_index(op.f('ix_raffle_ticket_id'), table_name='raffle_ticket')
    op.drop_table('raffle_ticket')
    op.drop_index(op.f('ix_booking_room_id'), table_name='booking')
    op.drop_index(op.f('ix_booking_id'), table_name='booking')
    op.drop_table('booking')
    op.drop_index(op.f('ix_raffle_prize_raffle_id'), table_name='raffle_prize')
    op.drop_index(op.f('ix_raffle_prize_id'), table_name='raffle_prize')
    op.drop_table('raffle_prize')
    op.drop_index(op.f('ix_raffle_pack_ticket_raffle_id'), table_name='raffle_pack_ticket')
    op.drop_index(op.f('ix_raffle_pack_ticket_id'), table_name='raffle_pack_ticket')
    op.drop_table('raffle_pack_ticket')
    op.drop_table('loan_content')
    op.drop_table('campaign_votes')
    op.drop_table('campaign_lists_membership')
    op.drop_table('booking_room')
    op.drop_table('amap_order_content')
    op.drop_index(op.f('ix_refresh_token_token'), table_name='refresh_token')
    op.drop_index(op.f('ix_refresh_token_client_id'), table_name='refresh_token')
    op.drop_table('refresh_token')
    op.drop_table('raffle_cash')
    op.drop_index(op.f('ix_raffle_id'), table_name='raffle')
    op.drop_index(op.f('ix_raffle_group_id'), table_name='raffle')
    op.drop_index(op.f('ix_raffle_description'), table_name='raffle')
    op.drop_table('raffle')
    op.drop_index(op.f('ix_notification_topic_membership_topic'), table_name='notification_topic_membership')
    op.drop_table('notification_topic_membership')
    op.drop_index(op.f('ix_notification_firebase_devices_firebase_device_token'), table_name='notification_firebase_devices')
    op.drop_table('notification_firebase_devices')
    op.drop_index(op.f('ix_loaner_item_id'), table_name='loaner_item')
    op.drop_table('loaner_item')
    op.drop_index(op.f('ix_loan_loaner_id'), table_name='loan')
    op.drop_index(op.f('ix_loan_id'), table_name='loan')
    op.drop_index(op.f('ix_loan_borrower_id'), table_name='loan')
    op.drop_table('loan')
    op.drop_table('core_user_email_migration_code')
    op.drop_table('core_membership')
    op.drop_table('campaign_lists')
    op.drop_table('campaign_has_voted')
    op.drop_index(op.f('ix_calendar_events_id'), table_name='calendar_events')
    op.drop_table('calendar_events')
    op.drop_table('booking_manager')
    op.drop_index(op.f('ix_amap_order_order_id'), table_name='amap_order')
    op.drop_index(op.f('ix_amap_order_delivery_id'), table_name='amap_order')
    op.drop_table('amap_order')
    op.drop_table('amap_delivery_content')
    op.drop_table('amap_cash')
    op.drop_table('advert_adverts')
    op.drop_index(op.f('ix_notification_message_firebase_device_token'), table_name='notification_message')
    op.drop_index(op.f('ix_notification_message_context'), table_name='notification_message')
    op.drop_table('notification_message')
    op.drop_table('module_visibility')
    op.drop_index(op.f('ix_loaner_id'), table_name='loaner')
    op.drop_table('loaner')
    op.drop_table('core_user_unconfirmed')
    op.drop_table('core_user_recover_request')
    op.drop_index(op.f('ix_core_user_id'), table_name='core_user')
    op.drop_index(op.f('ix_core_user_email'), table_name='core_user')
    op.drop_table('core_user')
    op.drop_index(op.f('ix_core_group_name'), table_name='core_group')
    op.drop_index(op.f('ix_core_group_id'), table_name='core_group')
    op.drop_table('core_group')
    op.drop_table('cinema_session')
    op.drop_table('campaign_voter_groups')
    op.drop_table('campaign_status')
    op.drop_table('campaign_sections')
    op.drop_index(op.f('ix_authorization_code_code'), table_name='authorization_code')
    op.drop_table('authorization_code')
    op.drop_index(op.f('ix_amap_product_name'), table_name='amap_product')
    op.drop_index(op.f('ix_amap_product_id'), table_name='amap_product')
    op.drop_index(op.f('ix_amap_product_category'), table_name='amap_product')
    op.drop_table('amap_product')
    op.drop_index(op.f('ix_amap_information_unique_id'), table_name='amap_information')
    op.drop_table('amap_information')
    op.drop_index(op.f('ix_amap_delivery_id'), table_name='amap_delivery')
    op.drop_index(op.f('ix_amap_delivery_delivery_date'), table_name='amap_delivery')
    op.drop_table('amap_delivery')
    op.drop_index(op.f('ix_advert_advertisers_id'), table_name='advert_advertisers')
    op.drop_table('advert_advertisers')
    # ### end Alembic commands ###
