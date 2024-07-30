from sqlalchemy.ext.asyncio import AsyncSession


class TransactionalAsyncSession(AsyncSession):
    """
    This class is a wrapper around the AsyncSession class

    It inherit from AsyncSession and can be used as a normal AsyncSession object.
    The TransactionalAsyncSession is thus retro-compatible with the AsyncSession object, you can use it with non transactional cruds.
    NOTE: the `commit` method is overridden to do nothing.

    To get an instance of this class, you can use the `get_transactional_db` dependency:
    ```python
    db: TransactionalAsyncSession = Depends(get_transactional_db())
    ```

    get_transactional_db will:
     - construct a AsyncSession object
     - wrap it in a TransactionalAsyncSession object and yield it
     - try to commit the transaction at the end and rollback if an error occurs

    This means that you don't need to call the `commit` method yourself.

    If you really need to commit manually, you can call the `commit_manually` method.
    This is only useful if you need to commit in the middle of a transaction.
    NOTE: the whole transaction will first be committed on `commit_manually`, you also need to manage any rollback yourself.
    """

    def __init__(self, db: AsyncSession) -> None:
        # Wrap the AsyncSession object
        self._db = db

    async def commit(self) -> None:
        # Do nothing
        pass

    async def commit_manually(self) -> None:
        await self._db.commit()

    def __getattr__(self, name: str):
        """
        Delegate attribute access to the wrapped object
        The method is called when an attribute is not found in the
        """
        return getattr(self._db, name)
