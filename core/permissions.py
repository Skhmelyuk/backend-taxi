from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Permission class that allows access only to admin users (is_staff).

    This permission checks:
        - User is authenticated
        - User has is_staff=True

    Attributes:
        None

    Methods:
        has_permission(request, view): Returns True if user is admin.
    """
    message = 'Only admin users can perform this action.'

    def has_permission(self, request, view) -> bool:
        """
        Check if authenticated user is admin.

        Args:
            request (Request): DRF request object.
            view (APIView): DRF view instance.

        Returns:
            bool: True if user is admin, False otherwise.
        """
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_staff", False)
        )


class IsDriverUser(permissions.BasePermission):
    """
    Permission class that allows access only to driver users.

    This permission checks:
        - User is authenticated
        - User has is_driver=True

    Methods:
        has_permission(request, view): Returns True if user is driver.
    """
    message = 'Only driver users can perform this action.'

    def has_permission(self, request, view) -> bool:
        """
        Check if authenticated user is driver.

        Args:
            request (Request): DRF request object.
            view (APIView): DRF view instance.

        Returns:
            bool: True if user is driver, False otherwise.
        """
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_driver", False)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows access to object owner or admin.

    Access rules:
        - Admin users have full access
        - Object owner has full access
        - Other users are denied access

    Object must have 'user' attribute or be user instance itself.
    """
    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Check if user is object owner or admin.

        Args:
            request (Request): DRF request object.
            view (APIView): DRF view instance.
            obj (Any): Object being accessed.

        Returns:
            bool: True if user is owner or admin, False otherwise.
        """

        if getattr(request.user, "is_staff", False):
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows read access to anyone,
    but write access only to object owner.

    Access rules:
        - SAFE_METHODS allowed for all users
        - Write methods allowed only for owner
    """
    message = 'You do not have permission to edit this resource.'

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Check if user can modify object or only read it.

        Args:
            request (Request): DRF request object.
            view (APIView): DRF view instance.
            obj (Any): Object being accessed.

        Returns:
            bool: True if allowed, False otherwise.
        """

        if request.method in permissions.SAFE_METHODS:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user


class IsVerifiedUser(permissions.BasePermission):
    """
    Permission class that allows access only to verified users.

    This permission checks:
        - User is authenticated
        - User has is_verified attribute set to True
    """
    message = 'Your account must be verified.'

    def has_permission(self, request, view) -> bool:
        """
        Check if authenticated user is verified.

        Args:
            request (Request): DRF request object.
            view (APIView): DRF view instance.

        Returns:
            bool: True if user is verified, False otherwise.
        """
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_verified", False)
        )


class AllowAny(permissions.AllowAny):
    """
    Permission class that allows unrestricted access.

    This is wrapper around DRF AllowAny for consistency
    with project architecture and imports.
    """
    pass
