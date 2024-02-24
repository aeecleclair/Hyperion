from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TodosItem(Base):
    # Le nom de la table dans la base de données est `todos_item`
    __tablename__ = "todos_item"

    # `index=true` permet de retrouver plus rapidement
    # les éléments par leur `id` ou `user_id` dans la base de données
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    # user_id est une relationship de type ForeignKey,
    # c'est à dire un champ qui fait référence au champ d'un autre model.
    # Ici on fait référence au champ `id` du modèle `core_user` (défini dans le ficher models_core).
    user_id: Mapped[str] = mapped_column(
        ForeignKey("core_user.id"), nullable=False, index=True
    )
    # Le nom de l'élément ne peut pas être None avec `nullable=false`
    name: Mapped[str] = mapped_column(String, nullable=False)
    creation: Mapped[date] = mapped_column(Date, nullable=False)
    # Au contraire, la deadline est optionnelle, elle peut donc contenir soit une `date` soit un objet `None`
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False)
