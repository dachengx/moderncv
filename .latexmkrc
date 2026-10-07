# Refresh the English CV's generated bibliography before up-to-date checks,
# and track the shared source during continuous (-pvc) builds.
use Cwd qw(abs_path);
use File::Basename qw(dirname basename);
use File::Spec;
use File::Glob qw(bsd_glob);

# latexmk evaluates rc files; __FILE__ does not identify this configuration.
my $cv_dir = dirname(abs_path($rc_files_read[-1]));
my $cv_script = File::Spec->catfile($cv_dir, 'scripts', 'sync_publications.py');
my $cv_source = $ENV{CV_PUBLICATIONS_SOURCE}
    || File::Spec->catfile(dirname($cv_dir), 'postdoc_application',
                          'Proposals', 'Publication_List', 'bibliography.bib');
$cv_source = File::Spec->rel2abs($cv_source, $cv_dir);
my $cv_output = File::Spec->catfile($cv_dir, 'publications.bib');
my $cv_other_output = File::Spec->catfile($cv_dir, 'publications-other.bib');
my $cv_python = $ENV{CV_PUBLICATIONS_PYTHON} || 'python3';

my $cv_sync = sub {
    system { $cv_python } $cv_python, $cv_script,
        '--source', $cv_source, '--output', $cv_output;
    die "Publication synchronization failed; CV compilation stopped.\n" if $?;
    system { $cv_python } $cv_python, $cv_script,
        '--source', $cv_source, '--output', $cv_other_output,
        '--selection', 'other';
    die "Other publication synchronization failed; CV compilation stopped.\n" if $?;
};

# Explicit template builds remain independent of the external publication repo.
my @cv_targets = @command_line_file_list;
my $cv_skip_arg = 0;
for my $arg (@ARGV) {
    if ($cv_skip_arg) { $cv_skip_arg = 0; next; }
    if ($arg =~ /^--?[re]$/) { $cv_skip_arg = 1; next; }
    next if $arg =~ /^-/;
    push @cv_targets, grep {
        /\.tex$/ || -f "$_.tex"
    } bsd_glob($arg);
}
my $cv_requested = @cv_targets
    ? scalar(grep { basename($_) =~ /^english(?:\.tex)?$/ } @cv_targets)
    : -f File::Spec->catfile($cv_dir, 'english.tex');
my $cv_nonbuild = scalar(grep { /^--?(?:c|C|CA|h|help|v|version)$/ } @ARGV);
$cv_sync->() if $cv_requested && !$cv_nonbuild;

add_hook('before_xlatex', sub {
    my %info = @_;
    $cv_sync->() if basename($info{tex_file}) eq 'english.tex';
});
add_hook('after_xlatex_analysis', sub {
    my %info = @_;
    return unless basename($info{tex_file}) eq 'english.tex';
    rdb_ensure_file($rule, $cv_source);
    rdb_ensure_file($rule, $cv_script);
});
