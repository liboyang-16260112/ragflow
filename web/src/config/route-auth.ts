type ProtectedRouteAuth = {
  embeddedAuth: boolean;
  authorization: string | null | undefined;
};

export const resolveProtectedRouteRedirect = ({
  embeddedAuth,
  authorization,
}: ProtectedRouteAuth): '/login' | null =>
  embeddedAuth || Boolean(authorization) ? null : '/login';
