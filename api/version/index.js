// Which commit is this production deployment? Vercel sets VERCEL_GIT_COMMIT_SHA when it builds a git push. Used by the DEPLOY.md check
// after a merge to main (a green build does not prove it is the deployment serving the domain; see BULLETIN 022). Public information:
// the repository is public and this returns only the commit, the deployment id and the environment name.
module.exports = (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.status(200).json({
    commit: process.env.VERCEL_GIT_COMMIT_SHA || null,
    deployment: process.env.VERCEL_DEPLOYMENT_ID || null,
    environment: process.env.VERCEL_ENV || null,
  });
};
