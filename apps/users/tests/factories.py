import factory
from factory.django import DjangoModelFactory
from apps.users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone_number = factory.Sequence(lambda n: f'+38050{n:07d}')
    role = User.Role.USER
    is_active = True
    is_verified = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or 'testpass123')
        self.save()


class AdminUserFactory(UserFactory):
    role = User.Role.ADMIN
    is_staff = True
    is_superuser = True


class DriverUserFactory(UserFactory):
    role = User.Role.DRIVER
