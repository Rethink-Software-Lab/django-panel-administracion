import graphene
from .querys import Query
from .mutations import Mutations


schema = graphene.Schema(query=Query, mutation=Mutations)

