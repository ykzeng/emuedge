for var in "$@"
do
    fname=$(basename $var)
    path=$var
    dist_path=./dist/$fname.dist
    
    cat $path | grep icmp_seq | cut -d'=' -f4 | cut -d' ' -f1 > tmp_rtt.log
    ./maketable tmp_rtt.log > $dist_path
    cp $dist_path /usr/lib64/tc/
    
    echo "${fname}" >> dist_db
    echo "$(./stats tmp_rtt.log)" >> dist_db
    rm -rf tmp_rtt.log
done

